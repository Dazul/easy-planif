from django.shortcuts import render
from django.views import generic
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect

from .models import *
from .forms import *

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
        #context['tasks'] = mark_safe('Hello')
        return context

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
