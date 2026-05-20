from rest_framework import viewsets, mixins, serializers as drf_serializers, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Meeting, MeetingParticipant
from .serializers import (
    MeetingSerializer, MeetingStatusSerializer,
    MeetingUploadSerializer, MeetingImportSerializer,
    LinkParticipantsSerializer,
)
from .parsers import extract_text_from_file
from .tasks import process_meeting, process_import
from apps.accounts.models import Person
from apps.accounts.views import get_user_org


@extend_schema_view(
    list=extend_schema(tags=['meetings'], summary='List org meetings'),
    retrieve=extend_schema(tags=['meetings'], summary='Meeting detail'),
    partial_update=extend_schema(tags=['meetings'], summary='Update meeting title, date, type, or summary'),
    participants=extend_schema(tags=['meetings'], summary='List participants — confirmed and unconfirmed'),
    add_participant=extend_schema(
        tags=['meetings'],
        summary='Add a person to a meeting',
        request=drf_serializers.Serializer,
    ),
    remove_participant=extend_schema(
        tags=['meetings'],
        summary='Remove a person from a meeting',
        request=drf_serializers.Serializer,
    ),
)
class MeetingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    http_method_names = ['get', 'patch', 'post', 'head', 'options']
    serializer_class = MeetingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = get_user_org(self.request)
        if org is None:
            return Meeting.objects.none()
        return (
            Meeting.objects.filter(organisation=org)
            .prefetch_related('topics')
            .order_by('-occurred_at')
        )

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        org = get_user_org(request)
        meeting = get_object_or_404(Meeting, id=pk, organisation=org)
        rows = (
            MeetingParticipant.objects
            .filter(meeting=meeting)
            .select_related('person')
            .order_by('person__name')
        )
        return Response([
            {
                'person': {
                    'id':    str(row.person.id),
                    'name':  row.person.name,
                    'email': row.person.email,
                    'role':  row.person.role,
                },
                'speaker_label': row.speaker_label or row.person.name,
                'confirmed':     row.confirmed,
            }
            for row in rows
        ])

    @action(detail=True, methods=['post'], url_path='add-participant')
    def add_participant(self, request, pk=None):
        """Add a person to this meeting. Pass person_id for existing or person{} to create new."""
        org = get_user_org(request)
        meeting = get_object_or_404(Meeting, id=pk, organisation=org)

        person_id = request.data.get('person_id')
        person_data = request.data.get('person')

        if person_id:
            try:
                person = Person.objects.get(pk=person_id, organisation=org)
            except Person.DoesNotExist:
                return Response({'detail': 'person_id not found.'}, status=status.HTTP_404_NOT_FOUND)
        elif person_data:
            if not person_data.get('name'):
                return Response({'detail': 'person.name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            person, _ = Person.objects.get_or_create(
                organisation=org,
                name=person_data['name'],
                defaults={
                    'email': person_data.get('email', ''),
                    'role':  person_data.get('role', ''),
                },
            )
        else:
            return Response({'detail': 'Provide person_id or person.'}, status=status.HTTP_400_BAD_REQUEST)

        mp, created = MeetingParticipant.objects.get_or_create(
            meeting=meeting,
            person=person,
            defaults={'confirmed': True},
        )
        if not created and not mp.confirmed:
            mp.confirmed = True
            mp.save(update_fields=['confirmed'])

        return Response({
            'person':    {'id': str(person.id), 'name': person.name, 'role': person.role},
            'confirmed': mp.confirmed,
            'created':   created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-participant')
    def remove_participant(self, request, pk=None):
        """Remove a person from this meeting by person_id."""
        org = get_user_org(request)
        meeting = get_object_or_404(Meeting, id=pk, organisation=org)

        person_id = request.data.get('person_id')
        if not person_id:
            return Response({'detail': 'person_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        deleted, _ = MeetingParticipant.objects.filter(
            meeting=meeting, person_id=person_id
        ).delete()

        if not deleted:
            return Response({'detail': 'Person is not a participant of this meeting.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['meetings'],
    summary='Upload meeting transcript',
    description=(
        'Submit a transcript as text or file. Returns 202 immediately. '
        'Gemini extracts commitments and participants asynchronously — '
        'poll /meetings/{id}/status/ until complete, then review both '
        'GET /meetings/{id}/participants/ and GET /commitments/?meeting={id}&status=pending_review '
        'in any order.'
    ),
    request=MeetingUploadSerializer,
    responses={202: MeetingStatusSerializer},
)
class MeetingUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MeetingUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transcript = data.get('transcript', '')
        if data.get('file'):
            transcript = extract_text_from_file(data['file'])

        meeting = Meeting.objects.create(
            organisation=org,
            title=data['title'],
            occurred_at=data['occurred_at'],
            platform=Meeting.Platform.UPLOAD,
            raw_transcript=transcript,
            word_count=len(transcript.split()),
            processing_status=Meeting.ProcessingStatus.PENDING,
        )

        process_meeting.delay(str(meeting.id))

        return Response(
            {'meeting_id': str(meeting.id), 'status': meeting.processing_status},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(
    tags=['meetings'],
    summary='Validate meeting participants',
    description=(
        'After Gemini extraction completes, confirm detected participants, re-link to the correct '
        'person, add new people, or skip. Can be called in any order relative to commitment review. '
        'Each confirmed entry sets confirmed=True on the MeetingParticipant row.'
    ),
    request=LinkParticipantsSerializer,
    responses={200: None},
)
class LinkParticipantsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        meeting = get_object_or_404(Meeting, id=pk, organisation=org)

        serializer = LinkParticipantsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entries = serializer.validated_data['participants']

        for entry in entries:
            if entry.get('skip'):
                # Remove from meeting if previously auto-linked
                if entry.get('person_id'):
                    MeetingParticipant.objects.filter(
                        meeting=meeting, person_id=entry['person_id']
                    ).delete()
                continue

            if entry.get('person_id'):
                try:
                    person = Person.objects.get(pk=entry['person_id'], organisation=org)
                except Person.DoesNotExist:
                    return Response(
                        {'detail': f"person_id {entry['person_id']} not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                new_data = entry['person']
                if not new_data.get('name'):
                    return Response(
                        {'detail': 'person.name is required when creating a new person.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                person, _ = Person.objects.get_or_create(
                    organisation=org,
                    name=new_data['name'],
                    defaults={
                        'email': new_data.get('email', ''),
                        'role':  new_data.get('role', ''),
                    },
                )

            mp, _ = MeetingParticipant.objects.get_or_create(
                meeting=meeting, person=person,
                defaults={'speaker_label': entry.get('detected_name', ''), 'confirmed': True},
            )
            if not mp.confirmed:
                mp.confirmed = True
                mp.save(update_fields=['confirmed'])

        return Response({
            'meeting_id':        str(meeting.id),
            'participant_count': MeetingParticipant.objects.filter(meeting=meeting).count(),
            'confirmed_count':   MeetingParticipant.objects.filter(meeting=meeting, confirmed=True).count(),
        })


@extend_schema(
    tags=['meetings'],
    summary='Import prior commitments document',
    description=(
        'Submit an existing tracker, Notion export, spreadsheet, or action-item list. '
        'Gemini extracts commitments as PENDING_REVIEW with source=import. '
        'Returns 202 immediately — poll /meetings/{id}/status/ until complete.'
    ),
    request=MeetingImportSerializer,
    responses={202: MeetingStatusSerializer},
)
class MeetingImportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MeetingImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        text = data.get('text', '')
        if data.get('file'):
            text = extract_text_from_file(data['file'])

        meeting = Meeting.objects.create(
            organisation=org,
            title=data.get('title', 'Prior Commitments Import'),
            occurred_at=timezone.now(),
            platform=Meeting.Platform.IMPORT,
            raw_transcript=text,
            word_count=len(text.split()),
            processing_status=Meeting.ProcessingStatus.PENDING,
        )

        process_import.delay(str(meeting.id))

        return Response(
            {'meeting_id': str(meeting.id), 'status': meeting.processing_status},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(
    tags=['meetings'],
    summary='Poll meeting processing status',
    description='Poll until status is "complete" or "failed". Then fetch commitments.',
    responses={200: MeetingStatusSerializer},
)
class MeetingStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        meeting = get_object_or_404(Meeting, id=pk, organisation=org)

        return Response({
            'meeting_id':        str(meeting.id),
            'status':            meeting.processing_status,
            'processed_at':      meeting.processed_at,
            'processing_error':  meeting.processing_error or None,
            'commitment_count':  meeting.commitments.count(),
            'participant_count': MeetingParticipant.objects.filter(meeting=meeting).count(),
            'confirmed_count':   MeetingParticipant.objects.filter(meeting=meeting, confirmed=True).count(),
        })
