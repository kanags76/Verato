from django.contrib import admin
from .models import Prompt, AICallLog


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display    = ['name', 'version', 'updated_at', 'updated_by']
    readonly_fields = ['version', 'updated_at', 'updated_by']
    search_fields   = ['name']

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        if change and obj.pk:
            try:
                obj.version = Prompt.objects.get(pk=obj.pk).version + 1
            except Prompt.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)


@admin.register(AICallLog)
class AICallLogAdmin(admin.ModelAdmin):
    list_display    = ['created_at', 'prompt_name', 'prompt_version', 'organisation', 'success', 'duration_ms', 'triggered_by']
    list_filter     = ['prompt_name', 'success', 'created_at']
    search_fields   = ['prompt_name', 'error', 'organisation__name']
    readonly_fields = [f.name for f in AICallLog._meta.get_fields() if hasattr(f, 'name')]
    ordering        = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
