# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-15 14:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0005_auto_20180809_1037'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='description',
            index_together=set([]),
        ),
        migrations.AddIndex(
            model_name='description',
            index=models.Index(fields=['toelichting', 'bronnenlijst', 'boek'], name='dictionary__toelich_a32e26_idx'),
        ),
        migrations.AddIndex(
            model_name='description',
            index=models.Index(fields=['toelichting', 'bronnenlijst'], name='dictionary__toelich_1b14eb_idx'),
        ),
    ]
