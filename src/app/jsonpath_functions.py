jsonpath_functions = {}

def register(func):
    jsonpath_functions[func.__name__] = func
    return func

@register
def first(result):
    return result[0]

@register
def last(result):
    return result[-1]

@register
def min(result):
    return min(result)

@register
def max(result):
    return max(result)

@register
def regex(result):
    # TODO : implment regex searching
    return result