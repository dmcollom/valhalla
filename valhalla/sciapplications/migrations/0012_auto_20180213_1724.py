# Generated by Django 2.0.2 on 2018-02-13 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sciapplications', '0011_auto_20180207_2314'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timerequest',
            name='std_time',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='timerequest',
            name='too_time',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
