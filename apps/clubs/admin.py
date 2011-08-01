# -*- coding: utf-8 -*-
from clubs.models import Club
from django.contrib import admin

class ClubAdmin(admin.ModelAdmin):
    list_display        = ('title', 'admin', 'address')
    list_filter         = ('title', 'admin', 'address')
    search_fields       = ('title', 'admin', 'address')
    


admin.site.register(Club, ClubAdmin)