from django.contrib import admin
from django.contrib.admin.views.main import ChangeList


class EncryptedPaginator:
    # TODO: Implement pagination for encrypted data. This paginator
    # currently returns all results in a single page.
    def __init__(self, queryset, per_page):
        self.queryset = queryset
        self.per_page = per_page

    def page(self, number):
        results = list(self.queryset)
        has_next = False
        return results, has_next


class EncryptedChangeList(ChangeList):
    def get_results(self, request):
        paginator = EncryptedPaginator(self.queryset, self.list_per_page)
        self.result_list, _ = paginator.page(self.page_num + 1)

        self.result_count = len(self.result_list)
        self.full_result_count = self.result_count

        self.can_show_all = True
        self.multi_page = False


class EncryptedModelAdmin(admin.ModelAdmin):
    def get_changelist(self, request, **kwargs):
        return EncryptedChangeList
