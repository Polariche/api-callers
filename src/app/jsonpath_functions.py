jsonpath_functions = {}

mx = max
mn = min

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
    return mn(result)

@register
def max(result):
    return mx(result)

@register
def regex(result):
    # TODO : implment regex searching
    return result