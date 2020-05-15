
class ChemicalException(Exception):
    "Base class for all Chemical Exceptions"


class TraitException(ChemicalException):
    "Any error having to do with traits"


class it:
    """
    You can extend `it` with methods that produce iterators and methods that
    produce a value. Decorate a class or a function with `trait` respectively to
    get this to work.
    """
    traits = {}

    def __init__(self, items=[]):
        self.items = iter(items)

    def __str__(self):
        return f'<{self.__class__.__name__} object at {hex(id(self))}>'

    def __iter__(self):
        return self

    def __reversed__(self):
        raise Exception('NOT IMPLEMENTED')

    def __next__(self):
        return next(self.items)

    def __dir__(self):
        from itertools import chain
        keys = set(self.__dict__.keys()) ^ {'items'}
        return sorted(set(chain(keys, self.traits.keys())))

    def __getattr__(self, name):
        if name not in it.traits:
            raise TraitException(
                f'Trait or extension method "{name}" not found for {self}.'
            )

        clazz = it.traits[name]

        class wrap:
            def __init__(self, items, clazz, name):
                self.items = items
                self.clazz = clazz
                self.name = name

            def __repr__(self):
                hid = hex(id(self.clazz))
                return f'<{self.__module__}.it.{self.name} at {hid}>'

            def __call__(self, *args, **kwargs):
                return self.clazz(self.items, *args, **kwargs)

        return wrap(self, clazz, name)

    def next(self):
        return next(self)


def trait(bind=None):
    def inner(*args, **kwargs):
        nonlocal bind
        return bind(*args, **kwargs)

    def wrapper(clazz):
        nonlocal bind
        it.traits[bind] = clazz
        return clazz

    if isinstance(bind, str):
        return wrapper

    it.traits[bind.__name__.lower()] = bind
    return inner


@trait('step_by')
class Step(it):
    def __init__(self, items, step):
        it.__init__(self, items)
        self.step = step

    def __next__(self):
        nxt = next(self.items)
        try:
            for _ in range(self.step - 1):
                next(self.items)
        except StopIteration:
            pass
        return nxt


@trait
class Filter(it):
    def __init__(self, items, filter_func):
        it.__init__(self, items)
        self.filter_func = filter_func

    def __next__(self):
        while res := next(self.items):
            if self.filter_func(res):
                return res


@trait('all')
def all_items_eval_to_true(self, func):
    return all(func(i) for i in self)


@trait
class Skip(it):
    def __init__(self, items, times):
        it.__init__(self, items)
        self.times = times
        for _ in range(times):
            next(self)


@trait
class Collect(it):
    def __init__(self, items, into=list):
        return into(items)


@trait
def nth(self, num):
    item = None
    for _ in range(num):
        item = next(self)
    return item


@trait
def count(self):
    return len(list(self))


@trait
def collect(self, into=list):
    return into(self)


@trait
def last(self):
    item = None
    for i in self:
        item = i
    return item


@trait
def take(self, num_items):
    return it(next(self) for i in range(num_items))


@trait
class Peekable(it):
    def __init__(self, items):
        it.__init__(self, items)
        self.ahead = None
        self.done = False

    def peek(self):
        if self.done:
            raise StopIteration()
        if not self.ahead:
            self.ahead = next(self.items)
        return self.ahead

    def __next__(self):
        if self.done:
            raise StopIteration()

        try:
            if not self.ahead:
                self.ahead = next(self.items)
        except StopIteration:
            ...

        ret = self.ahead
        try:
            self.ahead = next(self.items)
        except StopIteration:
            self.done = True
            return ret

        return ret


trait('max')(lambda self: max(self))
trait('min')(lambda self: min(self))

from itertools import chain, cycle

trait('chain')(lambda self, collection: it(chain(self, collection)))
trait('cycle')(lambda self: it(cycle(self)))
trait('map')(lambda self, closure: it(map(closure, self)))

@trait
def go(self):
    for i in self: ...


@trait
class Inspect(it):
    def __init__(self, items, func):
        it.__init__(self, items)
        self.func = func

    def __next__(self):
        item = next(self.items)
        self.func(item)
        return item

