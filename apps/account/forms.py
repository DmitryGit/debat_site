# -*- coding: utf-8 -*-
import re

from django import forms
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.encoding import smart_unicode
from django.utils.hashcompat import sha_constructor
from django.db.models.fields import BLANK_CHOICE_DASH, BLANK_CHOICE_NONE

from pinax.core.utils import get_send_mail
send_mail = get_send_mail()

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from clubs.models import Club, Verification
from profiles.models import Verification as profile_Verification

from emailconfirmation.models import EmailAddress
from account.models import Account

from timezones.forms import TimeZoneField
from account.models import PasswordReset
from recaptcha.fields import ReCaptchaField
import md5
import os

from django.forms import widgets
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import filesizeformat

from avatar.models import Avatar


alnum_re = re.compile(r'^\w+$')

class LoginForm(forms.Form):

    email = forms.EmailField(label = (u"Email"), required = True, widget = forms.TextInput())
    password = forms.CharField(label = (u"Password"), widget = forms.PasswordInput(render_value = False))
    remember = forms.BooleanField(label = (u"Remember Me"), help_text = (u"If checked you will stay logged in for 3 weeks"), required = False)

    user = None

    def clean(self):
        if self._errors:
            return
        user = authenticate(email = self.cleaned_data["email"], password = self.cleaned_data["password"])
        if user:
            if user.is_active:
                self.user = user
            elif user.is_active:
                raise forms.ValidationError((u"Профайл цього аккаунта ще не підтверджено адміністратором."))
        else:
            raise forms.ValidationError((u"Email та/або пароль невірний."))
        return self.cleaned_data

    def login(self, request):
        if self.is_valid():
            login(request, self.user)
            request.user.message_set.create(message = ugettext(u"Successfully logged in as %(username)s.") % {'username': self.user.username})
            if self.cleaned_data['remember']:
                request.session.set_expiry(60 * 60 * 24 * 7 * 3)
            else:
                request.session.set_expiry(0)
            return True
        return False

class UploadAvatarForm(forms.Form):

    avatar = forms.ImageField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(UploadAvatarForm, self).__init__(*args, **kwargs)

    def clean_avatar(self):
        data = self.cleaned_data['avatar']
        if AVATAR_ALLOWED_FILE_EXTS:
            (root, ext) = os.path.splitext(data.name.lower())
            if ext not in AVATAR_ALLOWED_FILE_EXTS:
               raise forms.ValidationError(
                _(u"%(ext)s is an invalid file extension. Authorized extensions are : %(valid_exts_list)s") %
                { 'ext' : ext, 'valid_exts_list' : ", ".join(AVATAR_ALLOWED_FILE_EXTS) })
        if data.size > AVATAR_MAX_SIZE:
            raise forms.ValidationError(
                _(u"Your file is too big (%(size)s), the maximum allowed size is %(max_valid_size)s") %
                { 'size' : filesizeformat(data.size), 'max_valid_size' : filesizeformat(AVATAR_MAX_SIZE)} )
        count = Avatar.objects.filter(user=self.user).count()
        if AVATAR_MAX_AVATARS_PER_USER > 1 and \
           count >= AVATAR_MAX_AVATARS_PER_USER:
            raise forms.ValidationError(
                _(u"You already have %(nb_avatars)d avatars, and the maximum allowed is %(nb_max_avatars)d.") %
                { 'nb_avatars' : count, 'nb_max_avatars' : AVATAR_MAX_AVATARS_PER_USER})
        return


class VKSiteWidget(widgets.TextInput):
    def render(self, name, value, attrs=None):
        result = super(VKSiteWidget, self).render(name, value, attrs=attrs)
        result += mark_safe(u'<input style ="float: right; margin-right: 33px; margin-top: 5px;"  type="button" value="Отримати мій id" onclick="return vk_signup();">')
        return result

class SignupForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
       # clubs = Club.objects.all()
        CLUBS = BLANK_CHOICE_DASH + ([(obj.id, obj.title) for obj in Club.objects.all()])
        self.base_fields['club'].choices = CLUBS

    ORG_WAYS = BLANK_CHOICE_DASH + [
        ('Методична робота', (u'Методична робота')),
        ('Розвиток англійських дебатів', (u'Розвиток англійських дебатів')),
        ('Організація дебатних заходів', (u'Організація дебатних заходів')),
        ('Співпраця із комерційними структурами', (u'Співпраця із комерційними структурами')),
        ('Співпраця  із іншими ГО', (u'Співпраця  із іншими ГО')),
        ('Співпраця із ЗМІ', (u'Співпраця із ЗМІ')),
        ('Не хочу займатись організаційними справами', (u'Не хочу займатись організаційними справами')),
    ]

    MEMBERS_FEE = BLANK_CHOICE_DASH + [
        ('5 грн', (u'5 грн')),
        ('10 грн', (u'10 грн')),
        ('15 грн', (u'15 грн')),
        ('20 грн', (u'20 грн')),
        ('30 грн', (u'30 грн')),
        ('50 грн', (u'50 грн')),
        ('Не можу сплачувати членський внесок', (u'Не можу сплачувати членський внесок')),
    ]

    CLUBS = BLANK_CHOICE_DASH + ([(obj.id, obj.title) for obj in Club.objects.all()])

    surname = forms.CharField(label = _(u'Прізвище'), max_length = 200, widget = forms.TextInput())
    name = forms.CharField(label = _(u'Ім’я'), max_length = 200, widget = forms.TextInput())
    middle_name = forms.CharField(label = _(u'По батькові'), max_length = 200, widget = forms.TextInput())

    birth_date = forms.DateField(label = _(u'Дата народження'), required = False)
    
    if settings.ACCOUNT_REQUIRED_EMAIL or settings.ACCOUNT_EMAIL_VERIFICATION:
        email = forms.EmailField(
            label = (u"Email"),
            required = True,
            widget = forms.TextInput()
        )
    else:
        email = forms.EmailField(
            label = (u"Email (optional)"),
            required = False,
            widget = forms.TextInput()
        )

    password1 = forms.CharField(label = (u"Password"), widget = forms.PasswordInput(render_value = False))
    password2 = forms.CharField(label = (u"Password (again)"), widget = forms.PasswordInput(render_value = False))


    address = forms.CharField(label = _(u'Поштова адреса'), max_length = 300, widget = forms.Textarea())
    phone = forms.CharField(label = _(u'Мобільний телефон'),max_length = 200, widget = forms.TextInput())
    skype = forms.CharField(label = _(u'Логін Skype'), max_length = 30, widget = forms.TextInput())
    icq = forms.IntegerField(label = _(u'ICQ'), max_value = 999999999, required = False, widget = forms.TextInput())
    vk_id = forms.CharField(label = (u'ID Вконтакті'), required = False, widget = VKSiteWidget())

    education = forms.CharField(label = _(u'Освіта (ВНЗ, факультет)'), max_length = 500, widget = forms.Textarea())
    work = forms.CharField(label = _(u'Місце роботи'), required = False, max_length = 300, widget = forms.Textarea())
    experience = forms.CharField(label = _(u'Опишіть у довільній формі досвід гри у дебати (роки участі у дебатах, турніри, в яких Ви брали участь, тощо).'), max_length = 600, widget = forms.Textarea())

    club = forms.ChoiceField(label = _(u'Дебатний клуб, який  представляєте (якщо є)'), choices = CLUBS, required = False, widget = forms.Select())
    social_work_exp = forms.CharField(label = _(u'Який досвід громадської роботи ви маєте(реалізовані проекти, членство в ГО, студ.самоврядуванні і т.д.)?'), required = False, max_length = 600, widget = forms.Textarea())
    desired_exp = forms.CharField(label = _(u'Які знання, досвід чи вміння ви хочете отримати, ставши членом ВМГО «ФДУ»?'), max_length = 200, widget = forms.Textarea())

    org_way = forms.ChoiceField(label = _(u'Яким організаційним напрямком в діяльності ВМГО «ФДУ» ви хотіли б займатись?'), choices = ORG_WAYS, initial = '', widget = forms.Select())

    members_fee = forms.ChoiceField(label = _(u'Який членський внесок ви готові сплачувати щомісячно?'), choices = MEMBERS_FEE, initial = '', widget = forms.Select())

    interests = forms.CharField(label = _(u'Напишіть, будь ласка, про свої цікаві захоплення та вміння'), max_length = 600, widget = forms.Textarea())

#    vk_id = forms.CharField(label = (u'ID Вконтакті'), required = False, widget = forms.HiddenInput())
    website = forms.URLField(label = _(u'Адреса сторінки в соціальній мережі (вконтакті, facebook тощо)'), required = False, widget = forms.HiddenInput())

    recaptcha = ReCaptchaField(error_messages = {
            'required': u'Це поле обов’язкове',
            'invalid' : u'Невірне значення'
            })

    confirmation_key = forms.CharField(max_length = 40, required = False, widget = forms.HiddenInput())

    def clean_email(self):
        username = self.cleaned_data["email"].replace('@', '_').replace('.', '_')
        email = self.cleaned_data["email"]
        try:
            user = User.objects.get(username__iexact = username)
        except User.DoesNotExist:
            return email
        raise forms.ValidationError(_(u"Користувач з таким email вже зареєстрований"))

    def clean(self):
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError((u"You must type the same password each time."))
        return self.cleaned_data

    def save(self):
        username = self.cleaned_data["email"]
        username = username.replace('@', '_')
        username = username.replace('.', '_')
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]


        if self.cleaned_data["confirmation_key"]:
            from friends.models import JoinInvitation # @@@ temporary fix for issue 93
            try:
                join_invitation = JoinInvitation.objects.get(confirmation_key = self.cleaned_data["confirmation_key"])
                confirmed = True
            except JoinInvitation.DoesNotExist:
                confirmed = False
        else:
            confirmed = False

        # @@@ clean up some of the repetition below -- DRY!

        if confirmed:
            if email == join_invitation.contact.email:
                new_user = User.objects.create_user(username, email, password)
                join_invitation.accept(new_user) # should go before creation of EmailAddress below
                new_user.message_set.create(message = ugettext(u"Your email address has already been verified"))
                # already verified so can just create
                EmailAddress(user = new_user, email = email, verified = True, primary = True).save()
            else:
                new_user = User.objects.create_user(username, "", password)
                join_invitation.accept(new_user) # should go before creation of EmailAddress below
                if email:
                    new_user.message_set.create(message = ugettext(u"Confirmation email sent to %(email)s") % {'email': email})
                    EmailAddress.objects.add_email(new_user, email)
        else:
            new_user = User.objects.create_user(username, "", password)
            if email:
                new_user.message_set.create(message = ugettext(u"Confirmation email sent to %(email)s") % {'email': email})
                EmailAddress.objects.add_email(new_user, email)

        new_user.last_name = self.cleaned_data["surname"]
        new_user.first_name = self.cleaned_data["name"]
        profile = new_user.get_profile()
        profile.surname = self.cleaned_data["surname"]
        profile.name = self.cleaned_data["name"]
        profile.middle_name = self.cleaned_data["middle_name"]
        profile.birth_date = self.cleaned_data["birth_date"]
        profile.address = self.cleaned_data["address"]
        profile.phone = self.cleaned_data["phone"]
        profile.skype = self.cleaned_data["skype"]
        profile.icq = self.cleaned_data["icq"]
        profile.website = self.cleaned_data["website"]
        profile.education = self.cleaned_data["education"]
        profile.work = self.cleaned_data["work"]
        profile.experience = self.cleaned_data["experience"]
        profile.social_work_exp = self.cleaned_data["social_work_exp"]
        profile.desired_exp = self.cleaned_data["desired_exp"]
        profile.org_way = self.cleaned_data["org_way"]
        profile.members_fee = self.cleaned_data["members_fee"]
        profile.interests = self.cleaned_data["interests"]
        profile.vk_id = self.cleaned_data["vk_id"]

        try:
            new_user.club_set.add(Club.objects.get(id = self.cleaned_data["club"]))
        except:
            pass

        profile.save()

        verification = profile_Verification()
        md5_hash = md5.new()
        md5_hash.update(new_user.username)
        verification.md5_hash = md5_hash.hexdigest()
        verification.profile = profile
        verification.save()

        if settings.ACCOUNT_EMAIL_VERIFICATION:
            new_user.is_active = False
            new_user.save()

        return username, password # required for authenticate()


#class OpenIDSignupForm(forms.Form):
#    username = forms.CharField(label = "Username", max_length = 30, widget = forms.TextInput())

#    if settings.ACCOUNT_REQUIRED_EMAIL or settings.ACCOUNT_EMAIL_VERIFICATION:
#        email = forms.EmailField(
#            label = (u"Email"),
#            required = True,
#            widget = forms.TextInput()
#        )
#    else:
#        email = forms.EmailField(
#            label = (u"Email (optional)"),
#            required = False,
#            widget = forms.TextInput()
#        )

#    def __init__(self, *args, **kwargs):
#        # remember provided (validated!) OpenID to attach it to the new user
#        # later.
#        self.openid = kwargs.pop("openid", None)

#        # pop these off since they are passed to this method but we can't
#        # pass them to forms.Form.__init__
#        kwargs.pop("reserved_usernames", [])
#        kwargs.pop("no_duplicate_emails", False)

#        super(OpenIDSignupForm, self).__init__(*args, **kwargs)

#    def clean_username(self):
#        if not alnum_re.search(self.cleaned_data["username"]):
#            raise forms.ValidationError(u"Usernames can only contain letters, numbers and underscores.")
#        try:
#            user = User.objects.get(username__iexact = self.cleaned_data["username"])
#        except User.DoesNotExist:
#            return self.cleaned_data["username"]
#        raise forms.ValidationError(u"This username is already taken. Please choose another.")


class UserForm(forms.Form):

    def __init__(self, user = None, *args, **kwargs):
        self.user = user
        super(UserForm, self).__init__(*args, **kwargs)


class AccountForm(UserForm):

    def __init__(self, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)
        try:
            self.account = Account.objects.get(user = self.user)
        except Account.DoesNotExist:
            self.account = Account(user = self.user)


class AddEmailForm(UserForm):

    email = forms.EmailField(label = (u"Email"), required = True, widget = forms.TextInput(attrs = {'size':'30'}))

    def clean_email(self):
        try:
            EmailAddress.objects.get(user = self.user, email = self.cleaned_data["email"])
        except EmailAddress.DoesNotExist:
            return self.cleaned_data["email"]
        raise forms.ValidationError((u"This email address already associated with this account."))

    def save(self):
        self.user.message_set.create(message = ugettext(u"Confirmation email sent to %(email)s") % {'email': self.cleaned_data["email"]})
        return EmailAddress.objects.add_email(self.user, self.cleaned_data["email"])


class ChangePasswordForm(UserForm):

    oldpassword = forms.CharField(label = (u"Current Password"), widget = forms.PasswordInput(render_value = False))
    password1 = forms.CharField(label = (u"New Password"), widget = forms.PasswordInput(render_value = False))
    password2 = forms.CharField(label = (u"New Password (again)"), widget = forms.PasswordInput(render_value = False))

    def clean_oldpassword(self):
        if not self.user.check_password(self.cleaned_data.get("oldpassword")):
            raise forms.ValidationError((u"Please type your current password."))
        return self.cleaned_data["oldpassword"]

    def clean_password2(self):
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError((u"You must type the same password each time."))
        return self.cleaned_data["password2"]

    def save(self):
        self.user.set_password(self.cleaned_data['password1'])
        self.user.save()
        self.user.message_set.create(message = ugettext(u"Password successfully changed."))


class SetPasswordForm(UserForm):

    password1 = forms.CharField(label = (u"Password"), widget = forms.PasswordInput(render_value = False))
    password2 = forms.CharField(label = (u"Password (again)"), widget = forms.PasswordInput(render_value = False))

    def clean_password2(self):
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError((u"You must type the same password each time."))
        return self.cleaned_data["password2"]

    def save(self):
        self.user.set_password(self.cleaned_data["password1"])
        self.user.save()
        self.user.message_set.create(message = ugettext(u"Password successfully set."))


class ResetPasswordForm(forms.Form):

    email = forms.EmailField(label = (u"Email"), required = True, widget = forms.TextInput(attrs = {'size':'30'}))

    def clean_email(self):
        if EmailAddress.objects.filter(email__iexact = self.cleaned_data["email"], verified = True).count() == 0:
            raise forms.ValidationError((u"Email address not verified for any user account"))
        return self.cleaned_data["email"]

    def save(self):
        for user in User.objects.filter(email__iexact = self.cleaned_data["email"]):
            temp_key = sha_constructor("%s%s%s" % (
                settings.SECRET_KEY,
                user.email,
                settings.SECRET_KEY,
            )).hexdigest()

            # save it to the password reset model
            password_reset = PasswordReset(user = user, temp_key = temp_key)
            password_reset.save()

            current_site = Site.objects.get_current()
            domain = unicode(current_site.domain)

            #send the password reset email
            subject = (u"Password reset email sent")
            message = render_to_string("account/password_reset_key_message.txt", {
                "user": user,
                "temp_key": temp_key,
                "domain": domain,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], priority = "high")
        return self.cleaned_data["email"]


class ResetPasswordKeyForm(forms.Form):

    password1 = forms.CharField(label = (u"New Password"), widget = forms.PasswordInput(render_value = False))
    password2 = forms.CharField(label = (u"New Password (again)"), widget = forms.PasswordInput(render_value = False))
    temp_key = forms.CharField(widget = forms.HiddenInput)

    def clean_temp_key(self):
        temp_key = self.cleaned_data.get("temp_key")
        if not PasswordReset.objects.filter(temp_key = temp_key, reset = False).count() == 1:
            raise forms.ValidationError((u"Temporary key is invalid."))
        return temp_key

    def clean_password2(self):
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError((u"You must type the same password each time."))
        return self.cleaned_data["password2"]

    def save(self):
        # get the password_reset object
        temp_key = self.cleaned_data.get("temp_key")
        password_reset = PasswordReset.objects.get(temp_key__exact = temp_key)

        # now set the new user password
        user = User.objects.get(passwordreset__exact = password_reset)
        user.set_password(self.cleaned_data["password1"])
        user.save()
        user.message_set.create(message = ugettext(u"Password successfully changed."))

        # change all the password reset records to this person to be true.
        for password_reset in PasswordReset.objects.filter(user = user):
            password_reset.reset = True
            password_reset.save()


class ChangeTimezoneForm(AccountForm):

    timezone = TimeZoneField(label = (u"Timezone"), required = True)

    def __init__(self, *args, **kwargs):
        super(ChangeTimezoneForm, self).__init__(*args, **kwargs)
        self.initial.update({"timezone": self.account.timezone})

    def save(self):
        self.account.timezone = self.cleaned_data["timezone"]
        self.account.save()
        self.user.message_set.create(message = ugettext(u"Timezone successfully updated."))


class ChangeLanguageForm(AccountForm):

    language = forms.ChoiceField(label = (u"Language"), required = True, choices = settings.LANGUAGES)

    def __init__(self, *args, **kwargs):
        super(ChangeLanguageForm, self).__init__(*args, **kwargs)
        self.initial.update({"language": self.account.language})

    def save(self):
        self.account.language = self.cleaned_data["language"]
        self.account.save()
        self.user.message_set.create(message = ugettext(u"Language successfully updated."))


# @@@ these should somehow be moved out of account or at least out of this module

from account.models import OtherServiceInfo, other_service, update_other_services

class TwitterForm(UserForm):
    username = forms.CharField(label = (u"Username"), required = True)
    password = forms.CharField(label = (u"Password"), required = True,
                               widget = forms.PasswordInput(render_value = False))

    def __init__(self, *args, **kwargs):
        super(TwitterForm, self).__init__(*args, **kwargs)
        self.initial.update({"username": other_service(self.user, "twitter_user")})

    def save(self):
        from microblogging.utils import get_twitter_password
        update_other_services(self.user,
            twitter_user = self.cleaned_data['username'],
            twitter_password = get_twitter_password(settings.SECRET_KEY, self.cleaned_data['password']),
        )
        self.user.message_set.create(message = ugettext(u"Successfully authenticated."))
