class JsonPath:
    @staticmethod
    def str(x):
        return list(map(str,x)) if type(x) is list else str(x)
    
    @staticmethod
    def int(x):
        return list(map(int,x)) if type(x) is list else int(x)
    
    @staticmethod
    def float(x):
        return list(map(float,x)) if type(x) is list else float(x)
    
    @staticmethod
    def max(x):
        return max(x)
    
    @staticmethod
    def min(x):
        return min(x)
    
    @staticmethod
    def len(x):
        return len(x)
    
    @staticmethod
    def avg(x):
        return sum(x)/len(x)
    
    @staticmethod
    def first(x):
        return x[0]
    
    @staticmethod
    def last(x):
        return x[-1]
    
    @staticmethod
    def regex(x):
        return x
    

class CssSelector:
    @staticmethod
    def str(x):
        return list(map(str,x)) if type(x) is list else str(x)
    
    @staticmethod
    def int(x):
        return list(map(int,x)) if type(x) is list else int(x)
    
    @staticmethod
    def first(x):
        return x[0]
    
    @staticmethod
    def last(x):
        return x[-1]