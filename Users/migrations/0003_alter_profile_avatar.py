# Generated by Django 5.2.1 on 2025-05-23 21:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0002_remove_profile_bio'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(default='logo.png', upload_to='profile_images'),
        ),
    ]
