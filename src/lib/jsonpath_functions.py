jsonpath_functions = {'str': lambda x: list(map(str,x)) if type(x) is list else str(x), 
                    'int': lambda x: list(map(int,x)) if type(x) is list else int(x), 
                    'float': lambda x: list(map(float,x)) if type(x) is list else float(x), 
                    'max': max, 
                    'min': min,
                    'len': len,
                    'avg': lambda x: sum(x)/len(x)
                    }

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
def regex(result):
    # TODO : implment regex searching
    return result