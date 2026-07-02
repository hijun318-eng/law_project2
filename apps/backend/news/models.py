from django.db import models

class NewsBookmark(models.Model):
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=1000)
    summary = models.TextField(blank=True)
    published_at = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'news_bookmark'

    def __str__(self):
        return self.title[:50]
