# -*- coding: utf-8 -*-
from datetime import datetime
from stdimage import StdImageField

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from photos.models import PhotoSet
from tagging.fields import TagField
from tagging.models import Tag
from photos.models import *
from pytils.translit import slugify
from django.utils.html import strip_tags

EXCERT_LENGTH = 75

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None


class Post(models.Model):
    """Post model."""

    STATUS_CHOICES = (
        (1, _(u'Чорновик')),
        (2, _(u'Опубліковано')),
    )
    title           = models.CharField(_(u'Назва'), max_length=200)
    slug            = models.SlugField()
   
    author          = models.ForeignKey(User, related_name="added_posts")
    creator_ip      = models.IPAddressField(_(u"IP адреса автора повідомлення"), blank=True, null=True)
    body            = models.TextField(_(u'Повідомлення'))
    status          = models.IntegerField(_(u'Статус'), choices=STATUS_CHOICES, default=2)
    status2         = models.BooleanField(_(u'Підтвердити'), default=False)
    allow_comments  = models.BooleanField(_(u'Дозволити коментарі'), default=True)
    publish         = models.DateTimeField(_(u'Опубліковано '), default=datetime.now)
    created_at      = models.DateTimeField(_(u'Створено'), default=datetime.now)
    updated_at      = models.DateTimeField(_(u'Змінено'))
    tags            = TagField(u'Теги')
    image = StdImageField(upload_to = "photos/", size=(300, 230), thumbnail_size=(150, 150))
    gallery = models.ForeignKey(PhotoSet, blank = True, null = True)
    class Meta:
        verbose_name        = _('post')
        verbose_name_plural = _('posts')
        ordering            = ('-publish',)
        get_latest_by       = 'publish'

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return ('blog_post', None, {
            'username': self.author.username,
            'year': self.publish.year,
            'month': "%02d" % self.publish.month,
            'slug': self.slug
    })
    get_absolute_url = models.permalink(get_absolute_url)

    def save(self, force_insert=False, force_update=False):
        self.slug=slugify(self.title)
        self.updated_at = datetime.now()
        super(Post, self).save(force_insert, force_update)
    
    @property
    def excert(self):
        stripped_body = strip_tags(self.body)
        if len(stripped_body) > EXCERT_LENGTH:
            excert = ''.join([stripped_body[:EXCERT_LENGTH], '...'])
        else:
            excert = stripped_body
        return excert
        


# handle notification of new comments
from threadedcomments.models import ThreadedComment
def new_comment(sender, instance, **kwargs):
    if isinstance(instance.content_object, Post):
        post = instance.content_object
        if notification:
            notification.send([post.author], "blog_post_comment",
                {"user": instance.user, "post": post, "comment": instance})
models.signals.post_save.connect(new_comment, sender=ThreadedComment)
