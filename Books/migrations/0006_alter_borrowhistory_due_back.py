# Generated by Django 5.2.1 on 2025-05-24 01:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Books', '0005_borrowhistory_adminaction_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='borrowhistory',
            name='due_back',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Срок возврата'),
        ),
    ]
