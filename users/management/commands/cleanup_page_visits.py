from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import PageVisit


class Command(BaseCommand):
    help = '清理过期的页面访问记录（默认保留 30 天）'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='保留天数（默认 30）')

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = PageVisit.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'已清理 {days} 天前的页面访问记录 {deleted} 条'))
