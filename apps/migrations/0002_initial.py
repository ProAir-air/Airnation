# Generated by Django 5.1.6 on 2025-03-05 14:26

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('apps', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='adminresponse',
            name='admin',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_responses', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='app',
            name='author',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='appdownloadhistory',
            name='app',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='apps.app'),
        ),
        migrations.AddField(
            model_name='appdownloadhistory',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='appfeedback',
            name='app',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='apps.app'),
        ),
        migrations.AddField(
            model_name='appfeedback',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='applicationrequest',
            name='request',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='adminresponse',
            name='request',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='apps.applicationrequest'),
        ),
        migrations.AddField(
            model_name='appreaction',
            name='app',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='apps.app'),
        ),
        migrations.AddField(
            model_name='appreaction',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='appviewhistory',
            name='app',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='apps.app'),
        ),
        migrations.AddField(
            model_name='appviewhistory',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='drivefile',
            name='app',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='drive_files', to='apps.app'),
        ),
        migrations.AddField(
            model_name='drivepermission',
            name='drive_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apps.drivefile'),
        ),
        migrations.AddField(
            model_name='drivepermission',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='feedback',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='feedbacks', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='feedbackresponse',
            name='feedback',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='apps.feedback'),
        ),
        migrations.AddField(
            model_name='feedbackresponse',
            name='responder',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='feedback_responses', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='linkclick',
            name='app',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='apps.app'),
        ),
        migrations.AddField(
            model_name='linkclick',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='notificationcomment',
            name='app',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='apps.app'),
        ),
        migrations.AddField(
            model_name='notificationcomment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='purchase',
            name='app',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='apps.app'),
        ),
        migrations.AddField(
            model_name='purchase',
            name='drive_file',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='apps.drivefile'),
        ),
        migrations.AddField(
            model_name='purchase',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='downloadtoken',
            name='purchase',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apps.purchase'),
        ),
        migrations.AddField(
            model_name='savedapp',
            name='app',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='apps.app'),
        ),
        migrations.AddField(
            model_name='savedapp',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='searchquery',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='appdownloadhistory',
            index=models.Index(fields=['downloaded_at'], name='apps_appdow_downloa_5a5238_idx'),
        ),
        migrations.AddIndex(
            model_name='appdownloadhistory',
            index=models.Index(fields=['device_type'], name='apps_appdow_device__d47ecc_idx'),
        ),
        migrations.AddIndex(
            model_name='appdownloadhistory',
            index=models.Index(fields=['download_format'], name='apps_appdow_downloa_58818e_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='appdownloadhistory',
            unique_together={('app', 'user', 'session_id', 'downloader_ip')},
        ),
        migrations.AlterUniqueTogether(
            name='appfeedback',
            unique_together={('app', 'user')},
        ),
        migrations.AlterUniqueTogether(
            name='appreaction',
            unique_together={('app', 'user')},
        ),
        migrations.AddIndex(
            model_name='appviewhistory',
            index=models.Index(fields=['app', 'viewed_at'], name='apps_appvie_app_id_ed0b5e_idx'),
        ),
        migrations.AddIndex(
            model_name='appviewhistory',
            index=models.Index(fields=['device_type'], name='apps_appvie_device__291847_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='appviewhistory',
            unique_together={('app', 'viewer_ip', 'session_id', 'user')},
        ),
        migrations.AddIndex(
            model_name='drivefile',
            index=models.Index(fields=['file_id'], name='apps_drivef_file_id_8d5e9a_idx'),
        ),
        migrations.AddIndex(
            model_name='drivefile',
            index=models.Index(fields=['is_active'], name='apps_drivef_is_acti_465d27_idx'),
        ),
        migrations.AddIndex(
            model_name='drivepermission',
            index=models.Index(fields=['permission_id'], name='apps_drivep_permiss_97b828_idx'),
        ),
        migrations.AddIndex(
            model_name='drivepermission',
            index=models.Index(fields=['email'], name='apps_drivep_email_9f0df4_idx'),
        ),
        migrations.AddIndex(
            model_name='drivepermission',
            index=models.Index(fields=['is_active'], name='apps_drivep_is_acti_8021c3_idx'),
        ),
        migrations.AddIndex(
            model_name='feedback',
            index=models.Index(fields=['feedback_type', 'status'], name='apps_feedba_feedbac_913ab7_idx'),
        ),
        migrations.AddIndex(
            model_name='feedback',
            index=models.Index(fields=['created_at'], name='apps_feedba_created_c84710_idx'),
        ),
        migrations.AddIndex(
            model_name='linkclick',
            index=models.Index(fields=['app', 'link_type'], name='apps_linkcl_app_id_2b0d8f_idx'),
        ),
        migrations.AddIndex(
            model_name='linkclick',
            index=models.Index(fields=['clicked_at'], name='apps_linkcl_clicked_856316_idx'),
        ),
        migrations.AddIndex(
            model_name='purchase',
            index=models.Index(fields=['purchase_id'], name='apps_purcha_purchas_e6e117_idx'),
        ),
        migrations.AddIndex(
            model_name='purchase',
            index=models.Index(fields=['payment_status'], name='apps_purcha_payment_fa7912_idx'),
        ),
        migrations.AddIndex(
            model_name='purchase',
            index=models.Index(fields=['payment_provider_ref'], name='apps_purcha_payment_611f0c_idx'),
        ),
        migrations.AddIndex(
            model_name='downloadtoken',
            index=models.Index(fields=['short_code'], name='apps_downlo_short_c_4c0ec7_idx'),
        ),
        migrations.AddIndex(
            model_name='downloadtoken',
            index=models.Index(fields=['expiry_time'], name='apps_downlo_expiry__3c2cf4_idx'),
        ),
        migrations.AddIndex(
            model_name='downloadtoken',
            index=models.Index(fields=['status'], name='apps_downlo_status_6398de_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='savedapp',
            unique_together={('user', 'app')},
        ),
        migrations.AddIndex(
            model_name='searchquery',
            index=models.Index(fields=['query', 'timestamp'], name='apps_search_query_d7b7c9_idx'),
        ),
    ]
