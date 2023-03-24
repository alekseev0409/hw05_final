from django.views.generic import CreateView
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from .forms import CreationForm


class SignUp(CreateView):
    form_class = CreationForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/signup.html'


class ChangePassword(PasswordChangeView):
    template_name = 'users/password_change_form.html'
    success_url = reverse_lazy('users:PasswordChangeDone')
