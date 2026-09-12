from django.contrib import admin, messages

from .models import ApiKey, generate_api_key


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'masked', 'is_active', 'used', 'quota', 'expires_at', 'last_used_at']
    list_filter = ['is_active']
    search_fields = ['name']
    readonly_fields = ['used', 'created_at', 'last_used_at']
    fields = ['name', 'owner', 'is_active', 'expires_at', 'quota', 'allowed_slugs']

    @admin.display(description='Key（脱敏）')
    def masked(self, obj):
        return obj.masked()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # 新建时默认激活（否则表单复选框默认未勾选，新建即吊销）
            form.base_fields['is_active'].initial = True
        return form

    def save_model(self, request, obj, form, change):
        if not change:
            full_key, key_hash = generate_api_key()
            obj.key_hash = key_hash
            obj.is_active = True  # 新建默认激活（复选框未勾选时表单不提交该字段）
            super().save_model(request, obj, form, change)
            messages.success(request, f'已生成 API Key（仅此一次展示，请妥善保存）：{full_key}')
        else:
            super().save_model(request, obj, form, change)
