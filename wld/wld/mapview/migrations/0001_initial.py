# Generated by Django 2.2 on 2023-04-24 07:24

from django.db import migrations, models
import wld.mapview.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.CharField(max_length=200, verbose_name='IP address')),
                ('reason', models.TextField(verbose_name='Reason')),
                ('created', models.DateTimeField(default=wld.mapview.models.get_current_datetime)),
                ('path', models.TextField(blank=True, null=True, verbose_name='Path')),
                ('body', models.TextField(blank=True, null=True, verbose_name='Body')),
            ],
        ),
    ]
