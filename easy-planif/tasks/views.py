from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import generic
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Tasks, Authorizations, CommentType, Comment
from .forms import AddTaskForm, AddAuthorizationForm, AddCommentTypeForm, AddCommentForm

# Create your views here.

class TasksView(generic.ListView):
    model = Tasks
    template_name = 'tasks.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = '<ul class="list-group">'
        for t in Tasks.objects.all():
            d += f'<li class="list-group-item"> {t.task_name} </li>'
        d += '</ul>'
        context['tasks'] = mark_safe(d)
        return context

class CommentsView(PermissionRequiredMixin, generic.ListView):
    model = Comment
    template_name = 'comments.html'
    permission_required = 'task.Trainer'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = ''
        for t in Comment.objects.all():
            d += f'<tr><td>{t.employee}</td><td>{t.comment}</td><td>{t.type}</td><td>{t.instructor}</td><td>{t.date}</td></tr>'
        context['comments'] = mark_safe(d)
        return context

class AuthorizationsView(PermissionRequiredMixin, generic.ListView):
    model = Authorizations
    template_name = 'authorizations.html'
    permission_required = 'task.Trainer'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = ''
        for t in Authorizations.objects.all():
            d += f'<tr><td> {t.user} </td><td> {t.task} </td></tr>'
        context['authorizations'] = mark_safe(d)
        return context

class CommentTypeView(generic.ListView):
    model = CommentType
    template_name = 'commentTypes.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff members only.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = '<ul class="list-group">'
        for t in CommentType.objects.all():
            d += f'<li class="list-group-item"> {t.comment_type} </li>'
        d += '</ul>'
        context['comment_types'] = mark_safe(d)
        return context

@staff_member_required
def add_task(request):
    if request.method == "POST":
        form = AddTaskForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/tasks")
    else:
        form = AddTaskForm()
    return render(request, "addTask.html", {"form": form})

@permission_required('task.Trainer', raise_exception=True)
def add_authorization(request):
    if request.method == "POST":
        form = AddAuthorizationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/authorizations")
    else:
        form = AddAuthorizationForm()
    return render(request, "addAuthorization.html", {"form": form})

@permission_required('task.Trainer', raise_exception=True)
def add_comment(request):
    if request.method == "POST":
        form = AddCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.instructor = request.user
            comment.save()
            return HttpResponseRedirect("/comments")
    else:
        form = AddCommentForm()
    return render(request, "addComment.html", {"form": form})

@staff_member_required
def add_comment_type(request):
    if request.method == "POST":
        form = AddCommentTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/commentTypes")
    else:
        form = AddCommentTypeForm()
    return render(request, "addCommentType.html", {"form": form})
