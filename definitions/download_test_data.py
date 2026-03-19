import pyku

for id in pyku.list_test_data(include_aliases=False):
    print(pyku.resources.get_test_data(id))
