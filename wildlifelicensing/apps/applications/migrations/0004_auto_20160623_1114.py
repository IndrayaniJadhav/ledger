# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-23 03:14
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wl_main', '0003_communicationslogentry'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wl_applications', '0003_auto_20160623_1114'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationlogentry',
            name='communicationslogentry_ptr',
            field=models.OneToOneField(auto_created=True, default=1, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wl_main.CommunicationsLogEntry'),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='CustomLogEntry',
        ),
        migrations.DeleteModel(
            name='EmailLogEntry',
        ),
        migrations.AddField(
            model_name='applicationrequest',
            name='application',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wl_applications.Application'),
        ),
        migrations.AddField(
            model_name='applicationrequest',
            name='officer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='amendmentrequest',
            name='applicationrequest_ptr',
            field=models.OneToOneField(auto_created=True, default=1, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wl_applications.ApplicationRequest'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='assessment',
            name='applicationrequest_ptr',
            field=models.OneToOneField(auto_created=True, default=1, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wl_applications.ApplicationRequest'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='idrequest',
            name='applicationrequest_ptr',
            field=models.OneToOneField(auto_created=True, default=1, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wl_applications.ApplicationRequest'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='returnsrequest',
            name='applicationrequest_ptr',
            field=models.OneToOneField(auto_created=True, default=1, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wl_applications.ApplicationRequest'),
            preserve_default=False,
        ),
    ]
