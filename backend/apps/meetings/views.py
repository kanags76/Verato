from rest_framework import viewsets, mixins, status
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
)
from .parsers import extract_text_from_file
from .tasks import process_meeting, process_import
from apps.accounts.models import Person
from apps.accounts.views import get_user_org


@extend_schema_view(
    list=extend_schema(tags=['meetings'], summary='List org meetings'),
    retrieve=extend_schema(tags=['meetings'], summary='Meeting detail'),
)
class MeetingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
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


@extend_schema(
    tags=['meetings'],
    summary='Upload meeting transcript',
    description=(
        'Submit a transcript as text or file. Returns 202 immediately. '
        'Gemini extraction runs asynchronously — poll /meetings/{id}/status/ until complete. '
        'Requires Celery worker to be running.'
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

        # Extract transcript text
        transcript = data.get('transcript', '')
        if data.get('file'):
            transcript = extract_text_from_file(data['file'])

        # Create meeting record
        meeting = Meeting.objects.create(
            organisation=org,
            title=data['title'],
            occurred_at=data['occurred_at'],
            platform=Meeting.Platform.UPLOAD,
            raw_transcript=transcript,
            word_count=len(transcript.split()),
            processing_status=Meeting.ProcessingStatus.PENDING,
        )

        # Resolve participant names → Person records → MeetingParticipant rows
        participant_names = [
            n.strip() for n in data.get('participants', '').split(',') if n.strip()
        ]
        for name in participant_names:
            person, _ = Person.objects.get_or_create(
                organisation=org, name=name,
                defaults={'email': ''},
            )
            MeetingParticipant.objects.get_or_create(meeting=meeting, person=person)

        # Queue extraction task
        process_meeting.delay(str(meeting.id))

        return Response(
            {'meeting_id': str(meeting.id), 'status': meeting.processing_status},
            status=status.HTTP_202_ACCEPTED,
        )


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
            'meeting_id':       str(meeting.id),
            'status':           meeting.processing_status,
            'processed_at':     meeting.processed_at,
            'processing_error': meeting.processing_error or None,
            'commitment_count': meeting.commitments.count(),
        })
