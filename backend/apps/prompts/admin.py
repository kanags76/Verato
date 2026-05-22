from django.contrib import admin
from .models import Prompt


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
