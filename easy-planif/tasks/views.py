from django.shortcuts import render
from django.views import generic
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect

from .models import Tasks, Authorizations, CommentType
from .forms import AddTaskForm, AddAuthorizationForm, AddCommentTypeForm

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

class AuthorizationsView(generic.ListView):
    model = Authorizations
    template_name = 'authorizations.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = '<table><tr><th>User</th><th>Task</th></tr>'
        for t in Authorizations.objects.all():
            d += f'<tr><td> {t.user} </td><td> {t.task} </td></tr>'
        d += '</table>'
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

def get_authorizations(request):
    query_results = Authorizations.objects.all()
    return render(request, "authorizations.html", {'query_results': query_results})

def comment_types(request):
    query_results = CommentType.objects.all()
    return render(request, "commentTypes.html", {'query_results': query_results})

def add_task(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = AddTaskForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            form.save()
            return HttpResponseRedirect("/tasks")

    # if a GET (or any other method) we'll create a blank form
    else:
        form = AddTaskForm()

    return render(request, "addTask.html", {"form": form})

def add_authorization(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = AddAuthorizationForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            form.save()
            return HttpResponseRedirect("/authorizations")

    # if a GET (or any other method) we'll create a blank form
    else:
        form = AddAuthorizationForm()

    return render(request, "addAuthorization.html", {"form": form})

def add_comment_type(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = AddCommentTypeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            form.save()
            return HttpResponseRedirect("/commentTypes")

    # if a GET (or any other method) we'll create a blank form
    else:
        form = AddCommentTypeForm()

    return render(request, "addCommentType.html", {"form": form})
