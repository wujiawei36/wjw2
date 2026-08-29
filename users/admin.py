from django.contrib.contenttypes.models import ContentType
from .models import CustomUser, Notification, Ban_IP, InviteCode, generate_invite_code
from django.contrib.sessions.models import Session
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from django.contrib import admin, messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from hijack.contrib.admin import HijackUserAdminMixin


@admin.register(CustomUser)
class CustomUserAdmin(HijackUserAdminMixin, UserAdmin):
    # 注意：HijackUserAdminMixin 会自动在列表末尾注入劫持按钮列，无需手动声明
    list_display = ["id"] + list(UserAdmin.list_display) + ["is_superuser", "password_status", "can_develop", "is_active", "need_email_active"]
    ordering = ["id"]  # 默认按 id 升序

    @admin.display(description="启用密码", ordering="password")
    def password_status(self, obj):
        if obj.has_usable_password():
            return mark_safe('<img src="/static/admin/img/icon-yes.svg" alt="True">')
        else:
            return mark_safe('<img src="/static/admin/img/icon-no.svg" alt="True">')

    # 编辑页的字段布局
    fieldsets = UserAdmin.fieldsets + (
        ('权限', {'fields': ('can_develop',)}),
        ('特殊', {'fields': ('need_email_active',)}),
    )

    # 新增用户时的字段
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('权限', {'fields': ('can_develop',)}),
        ('特殊', {'fields': ('need_email_active',)}),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "target_user"]
    ordering = ["id"]

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    # 后台列表显示的列
    list_display = [
        'action_time',      # 操作时间
        'user',             # 操作人
        'content_type',     # 修改的模型（比如 Users | 用户）
        'object_repr',      # 被修改的对象名称（比如具体是哪个用户）
        'action_flag',      # 动作类型（1=新增，2=修改，3=删除）
        'change_message',   # 具体的修改内容
    ]
    
    # 列表页右侧的过滤器（可以根据用户、动作类型筛选）
    list_filter = [
        'action_time',
        'user',
        'content_type',
        'action_flag'
    ]
    
    # 搜索框（可以根据操作人或对象名称搜索）
    search_fields = [
        'user__username',
        'object_repr'
    ]
    
    # 禁用添加按钮（日志是自动生成的，不允许手动新建）
    def has_add_permission(self, request):
        return False

    # 禁用删除：防止管理员删除操作日志（含列表页批量删除与详情页删除按钮）。
    # 需要恢复时删掉这个方法即可。
    def has_delete_permission(self, request, obj=None):
        return False

    # 禁用修改：日志只能查看，任何编辑一律拒绝（编辑页亦只读）
    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    # 所有字段设为只读，不允许修改任何历史记录
    readonly_fields = [
        'action_time',
        'user',
        'content_type',
        'object_id',
        'object_repr',
        'action_flag',
        'change_message'
    ]

# 2. 内容类型（只读查看）
@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    list_display = ['app_label', 'model']
    search_fields = ['app_label', 'model']
    list_filter = ['app_label']
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

# 3. 会话管理（可删除 = 踢人）
@admin.action(description='清理过期会话')
def clear_expired_sessions(modeladmin, request, queryset):
    count, _ = Session.objects.filter(expire_date__lt=timezone.now()).delete()
    messages.success(request, f'已清理 {count} 条过期会话')

@admin.action(description='清理所有会话（包括自己）')
def clear_all_sessions(modeladmin, request, queryset):
    # 先记下自己是不是在里面
    my_key = request.session.session_key

    count, _ = queryset.delete()

    # 如果把自己也删了，主动登出并跳转
    if my_key:
        logout(request)
        messages.warning(request, f'已清理 {count} 条会话（包括你自己）')
        return redirect('/admin/login/')

    messages.success(request, f'已清理 {count} 条会话')

# 如果之前已经注册过，需要先注销（防止报错）
try:
    admin.site.unregister(Session)
except admin.sites.NotRegistered:
    pass

@admin.register(Session)
class CustomSessionAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'userid', 'ip_address', 'expire_date']

    def userid(self, obj):
        """从 session 数据中取出用户 ID"""
        session_data = obj.get_decoded()
        user_id = session_data.get('_auth_user_id')
        if user_id:
            try:
                User = get_user_model()
                return User.objects.get(id=user_id).id
            except User.DoesNotExist:
                pass
        return '未登录'
    userid.short_description = '用户id'

    def ip_address(self, obj):
        """从 session 数据中取出 IP"""
        session_data = obj.get_decoded()
        return session_data.get('ip_address', '无')
    ip_address.short_description = 'IP 地址'
    actions = [clear_expired_sessions, clear_all_sessions]  # ← 加这一行
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

@admin.register(Ban_IP)
class Ban_IP_Admin(admin.ModelAdmin):
    list_display = ["ip", "active", "expires_at", "updated_at"]
    ordering = ["updated_at"]  # 默认按时间升序
    list_filter = ["active", "updated_at"]
    search_fields = ["ip"]


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'status_text', 'created_by', 'created_at', 'expires_at', 'used_at', 'used_by']
    list_filter = ['expires_at']
    search_fields = ['code', 'used_by__username']
    # 使用信息只能看不能改（一次性、绑定注册账号）
    readonly_fields = ['created_by', 'created_at', 'used_at', 'used_by']
    actions = ['create_7d_invite_codes', 'create_30d_invite_codes']

    @admin.display(description='状态')
    def status_text(self, obj):
        return obj.status_text

    def save_model(self, request, obj, form, change):
        # 新建时自动生成邀请码、默认创建者为当前管理员
        if not obj.code:
            obj.code = generate_invite_code()
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='生成 3 个有效期 7 天的邀请码')
    def create_7d_invite_codes(self, request, queryset):
        self._bulk_create_codes(request, days=7)

    @admin.action(description='生成 3 个有效期 30 天的邀请码')
    def create_30d_invite_codes(self, request, queryset):
        self._bulk_create_codes(request, days=30)

    def _bulk_create_codes(self, request, days):
        count = 0
        for _ in range(3):
            InviteCode.objects.create(
                code=generate_invite_code(),
                created_by=request.user,
                expires_at=timezone.now() + timedelta(days=days),
            )
            count += 1
        messages.success(request, f'已生成 {count} 个有效期 {days} 天的邀请码')

# ==================== django-axes 记录（只读） ====================
# 三个页面：Access attempts(失败聚合) / Access failures(失败流水) / Access logs(成功登录)
# 全部只读：不能增删改，防止攻击者删除攻击痕迹

from axes.models import AccessAttempt, AccessFailureLog, AccessLog


class ReadOnlyAxesAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True


@admin.register(AccessAttempt)
class AccessAttemptAdmin(ReadOnlyAxesAdmin):
    list_display = ["username", "ip_address", "failures_since_start", "locked_out", "attempt_time"]
    list_filter = ["attempt_time"]
    search_fields = ["username", "ip_address"]
    # post_data/get_data 含登录提交的明文密码，不在后台展示，防止泄露
    exclude = ("get_data", "post_data")

    @admin.display(description="已达锁定阈值", boolean=True)
    def locked_out(self, obj):
        from django.conf import settings as dj_settings
        return obj.failures_since_start >= dj_settings.AXES_FAILURE_LIMIT


@admin.register(AccessFailureLog)
class AccessFailureLogAdmin(ReadOnlyAxesAdmin):
    list_display = ["username", "ip_address", "locked_out", "attempt_time"]
    list_filter = ["attempt_time"]
    search_fields = ["username", "ip_address"]


@admin.register(AccessLog)
class AccessLogAdmin(ReadOnlyAxesAdmin):
    list_display = ["username", "ip_address", "attempt_time", "logout_time"]
    list_filter = ["attempt_time"]
    search_fields = ["username", "ip_address"]
