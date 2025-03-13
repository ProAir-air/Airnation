from django.contrib import admin
from .models import FeedbackResponse,Feedback,App,AppViewHistory,NotificationComment,ApplicationRequest,AppDownloadHistory,SavedApp,AppFeedback,SearchQuery,AppReaction,LinkClick,ApplicationRequest, AdminResponse


# Register your models here.
admin.site.register(FeedbackResponse)
admin.site.register(Feedback)
admin.site.register(App)
admin.site.register(AppViewHistory)
admin.site.register(AppDownloadHistory)
admin.site.register(SavedApp)
admin.site.register(AppFeedback)
admin.site.register(SearchQuery)
admin.site.register(AppReaction)
admin.site.register(LinkClick)
admin.site.register(ApplicationRequest)
admin.site.register(NotificationComment)
                    
                    
class AdminResponseInline(admin.StackedInline):
    """Allows admin to respond directly inside ApplicationRequest admin page"""
    model = AdminResponse
    extra = 1


@admin.register(AdminResponse)
class AdminResponseAdmin(admin.ModelAdmin):
    list_display = ("request", "admin", "is_visible", "responded_at")
    list_filter = ("is_visible", "responded_at")
    search_fields = ("request__app_name", "admin__username")
