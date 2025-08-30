from django.shortcuts import render
from django.views import generic
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect

from .models import Tasks, Authorizations, CommentType, Comment
from .forms import AddTaskForm, AddAuthorizationForm, AddCommentTypeForm, AddCommentForm

# Create your views here.

class TasksView(generic.ListView):
    model = Tasks
    template_name = 'tasks.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = ''
        for t in Tasks.objects.all():
            d += f'<li> {t.task_name} </li>'
        context['tasks'] = mark_safe(d)
        return context

class CommentsView(generic.ListView):
    model = Comment
    template_name = 'comments.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = ''
        for t in Comment.objects.all():
            d += f'<tr><td>{t.employee}</td><td>{t.comment}</td><td>{t.type}</td><td>{t.instructor}</td><td>{t.date}</td></tr>'
        context['comments'] = mark_safe(d)
        return context

class AuthorizationsView(generic.ListView):
    model = Authorizations
    template_name = 'authorizations.html'

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = ''
        for t in CommentType.objects.all():
            d += f'<li> {t.comment_type} </li>'
        context['comment_types'] = mark_safe(d)
        return context

def add_task(request):
    if request.method == "POST":
        form = AddTaskForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/tasks")
    else:
        form = AddTaskForm()
    return render(request, "addTask.html", {"form": form})

def add_authorization(request):
    if request.method == "POST":
        form = AddAuthorizationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/authorizations")
    else:
        form = AddAuthorizationForm()
    return render(request, "addAuthorization.html", {"form": form})

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

def add_comment_type(request):
    if request.method == "POST":
        form = AddCommentTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/commentTypes")
    else:
        form = AddCommentTypeForm()
    return render(request, "addCommentType.html", {"form": form})
