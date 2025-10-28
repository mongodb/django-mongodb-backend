from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.main import ChangeList
from django.core.paginator import InvalidPage, Paginator
from django.utils.functional import cached_property


class EncryptedPaginator(Paginator):
    @cached_property
    def count(self):
        return len(self.object_list)


class EncryptedChangeList(ChangeList):
    def get_results(self, request):
        """
        This is django.contrib.admin.views.main.ChangeList.get_results with
        a single modification to avoid COUNT queries.
        """
        paginator = self.model_admin.get_paginator(request, self.queryset, self.list_per_page)
        result_count = paginator.count
        if self.model_admin.show_full_result_count:
            # Modification: avoid COUNT query by using len() on the root queryset
            full_result_count = len(self.root_queryset)
        else:
            full_result_count = None
        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page
        if (self.show_all and can_show_all) or not multi_page:
            result_list = self.queryset._clone()
        else:
            try:
                result_list = paginator.page(self.page_num).object_list
            except InvalidPage as err:
                raise IncorrectLookupParameters from err
        self.result_count = result_count
        self.show_full_result_count = self.model_admin.show_full_result_count
        self.show_admin_actions = not self.show_full_result_count or bool(full_result_count)
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator


class EncryptedModelAdmin(admin.ModelAdmin):
    """
    A ModelAdmin that uses EncryptedPaginator and EncryptedChangeList
    to avoid COUNT queries in the admin changelist.
    """

    def get_paginator(self, request, queryset, per_page):
        return EncryptedPaginator(queryset, per_page)

    def get_changelist(self, request, **kwargs):
        return EncryptedChangeList
