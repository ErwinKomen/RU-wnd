# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-12-17 08:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0006_auto_20180815_1405'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coordinate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kloeke', models.CharField(default='xxxxxx', max_length=6, verbose_name='Plaatscode (Kloeke)')),
                ('place', models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Place name')),
                ('province', models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Province')),
                ('country', models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Country')),
                ('dictionary', models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Dictionary')),
                ('point', models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Coordinates')),
            ],
        ),
        migrations.AddField(
            model_name='dialect',
            name='count',
            field=models.IntegerField(default=0, verbose_name='Number of entries'),
        ),
        migrations.AddField(
            model_name='dialect',
            name='streek',
            field=models.CharField(db_index=True, default='(unknown)', max_length=100, verbose_name='Streek'),
        ),
        migrations.AddField(
            model_name='dialect',
            name='coordinate',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='coordinatedialects', to='dictionary.Coordinate'),
        ),
    ]