# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-05-01 07:14
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wildlifecompliance', '0041_auto_20180427_1955'),
    ]

    operations = [
        migrations.AddField(
            model_name='wildlifelicenceactivitytype',
            name='schema',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=list),
        ),
    ]
