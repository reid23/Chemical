import math
from . import it, trait, ChemicalException, NothingToPeek, Ref
import itertools
from collections.abc import Iterable

@trait
class Skip(it):
    """
    Lazily skip a number of items in the iterator chain.

    **Examples**

        :::python

        assert it('asdf').skip(1).collect(str) == 'sdf'
        assert it('asdf').rev().skip(1).rev().collect(str) == 'asd'
    """

    def __init__(self, items, times):
        it.__init__(self, items)
        self.times = times
        assert times > 0, 'skip: number of items to skip must be > 0'
        self._lower_bound = max(0, self._lower_bound - times)
        if self._upper_bound:
            self._upper_bound -= times
    
    def __get_next__(self):
        while self.times > 0:
            next(self.items)
            next(self.reverse)
            self.times -= 1

        return next(self.items)

    def __get_reversed__(self):
        """
        Although subtle, it is important that `next(self.items)` is called the
        same amount of times as `self.reverse`.
        """
        last_item = [next(self.items) for _ in range(self.times)]

        if last_item:
            last_item = last_item[-1]
        else:
            raise StopIteration('skip: reversing collection yields no elements')

        revv = it(
            self.reverse,
            self.items,
            self.size_hint()
        ).take_while(lambda x: id(x) != id(last_item))

        # NOTE(pebaz): Manually hide the size-hint that take_while provides
        return it(revv, bounds=self.size_hint())


@trait('step_by')
class Step(it):
    """
    If > 1, the number of elements to skip between each returned value.

    **Examples**

        :::python

        assert it(range(10)).step_by(2).collect() == [0, 2, 4, 6, 8]
        assert it(range(10)).rev().step_by(3).collect() == [9, 6, 3, 0]
    """
    def __init__(self, items, step):
        it.__init__(self, items)
        self.step = step

        self._lower_bound = max(0, int(math.ceil(self._lower_bound / step)))
        if self._upper_bound:
            self._upper_bound = int(math.ceil(self._upper_bound / step))

    def __get_next__(self):
        nxt = next(self.items)
        try:
            for _ in range(self.step - 1):
                next(self.items)
        except StopIteration:
            pass
        return nxt

    def __get_reversed__(self):
        return it(Step(self.reverse, self.step), self.items, self.size_hint())


@trait('filter')
def filter_it(self, filter_func):
    """
    Filters out elements of the iterator based on the provided lambda.

    **Examples**

        :::python

        assert it(range(5)).filter(lambda x: not x % 2).collect() == [0, 2, 4]
        assert it('abcd').filter(lambda x: x in 'bd').collect(str) == 'bd'
    """
    return it(
        filter(filter_func, self),
        None if self.reverse is None else filter(filter_func, self.reverse),
        (0, self._upper_bound)
    )


@trait
def take(self, num_items):
    """
    Returns only the number of items you specify from an iterator.

    **Examples**

        :::python

        assert it(range(5)).take(2).collect() == [0, 1]
        assert it(range(5)).rev().take(3).collect() == [4, 3, 2]
    """
    return it(
        itertools.islice(self, num_items), 
        None if self.reverse is None else itertools.islice(self.reversed, num_items), 
    [num_items] * 2)

@trait
def islice(self, *args):
    """
    slice using the standard start/stop/step interface. 
    Does not support negative step sizes or indices, but
    passing `None` is supported.

    **Examples**

        :::python

        assert it(range(10)).islice(2).collect() == [0, 1]
        assert it(range(10)).islice(2, 5).collect() == [2, 3, 4]
        assert it(range(10)).islice(4, None, 2).collect() == [4, 6, 8]
    """

    return it(
        itertools.islice(self, *args),
        None if self.reverse is None else itertools.islice(self.reverse, *args),
        (0, self.size_hint()[1])
    )

@trait
def take_while(self, closure):
    """
    Only returns elements from the iterator while a given function returns True.

    **Examples**

        :::python

        assert it('ab7f').take_while(lambda x: x.isalpha()).collect(str) == 'ab'
    """
    
    return it(
        itertools.takewhile(closure, self),
        None if self.reverse is None else itertools.takewhile(closure, self.reverse),
        (0, self.size_hint()[1])
    )


@trait
class Peekable(it):
    """
    Adds a method to any iterator that allows the next element to be revealed
    without consuming it.

    **Examples**

        :::python

        itr = it('cba').rev().peekable()
        assert itr.peek() == 'a'
        assert itr.next() == 'a'
        assert itr.peek() == 'b'
        assert itr.next() == 'b'
        assert itr.peek() == 'c'
        assert itr.next() == 'c'
    """
    def __init__(self, items):
        it.__init__(self, items)
        self.ahead = None
        self.done = False
        self.can_peek = True

    def has_next(self):
        try:
            self.peek()
        except NothingToPeek:
            self.can_peek = False
        return self.can_peek

    def peek(self):
        if self.done:
            raise NothingToPeek()

        if not self.ahead:
            try:
                self.ahead = next(self.items)
            except StopIteration as e:
                #self.done = True
                raise NothingToPeek().with_traceback(e.__traceback__) from e

        return self.ahead

    def __get_next__(self):
        if self.done:
            raise StopIteration()

        try:
            if not self.ahead:
                self.ahead = next(self.items)
        except StopIteration as e:
            pass

        ret = self.ahead
        try:
            self.ahead = next(self.items)
        except StopIteration:
            self.done = True
            return ret

        return ret


@trait('chain')
def chain_it(self, itr):
    """
    Chains multiple iterators together, yielding each element in turn.

    **Examples**

        :::python

        assert it('ab').chain('cd').collect(str) == 'abcd'
        assert it('ab').chain('cd').rev().collect(str) == 'dcba'
    """
    chained = it(itr)
    return it(
        itertools.chain(self, chained),
        None if ((chained.reverse is None) or (self.reverse is None)) else itertools.chain(
            chained.rev() if isinstance(chained, it) else reversed(chained),
            self.rev()
        ),
        (
            self._lower_bound + chained._lower_bound,
            self._upper_bound + chained._upper_bound
        )
    )


@trait('cycle')
def cycle_it(self):
    """
    Continuously returns the elements of the underlying iterator.

    Without being limited in some way, this iterator will never raise the
    `StopIteration` exception so be careful when using it in loops.

    **Examples**

        :::python

        assert it('123').cycle().take(6).collect(str) == '123123'
    """
    return it(
        itertools.cycle(self), 
        None if self.reverse is None else itertools.cycle(self.reverse)
    )


@trait('map')
def map_it(self, closure):
    """
    Applies a given function to each element and returns the result instead.

    **Examples**

        :::python

        assert it('abc').map(lambda x: x.upper()).collect(str) == 'ABC'
    """
    return it(
        map(closure, self),
        None if self.reverse is None else map(closure, self.reverse),
        self.size_hint()
    )

@trait
def starmap(self, closure):
    """
    Applies a given function to each element, unpacking each element into arguments

    **Examples**
    
        :::python

        assert it([[1,2],[3,4],[5,6]]).starmap(operator.mul).collect() == [2, 12, 30]
    """
    return self.map(lambda args: closure(*args))

@trait('enumerate')
def enumerate_it(self):
    """
    Yields a tuple containing the position and the value of each element.

    **Examples**

        :::python

        assert it((1, 2, 3)).enumerate().collect() == [(0, 1), (1, 2), (2, 3)]
    """
    return it(enumerate(self), None if self.reverse is None else enumerate(self.reverse), self.size_hint())


@trait
class Inspect(it):
    """
    Allows a function to be applied to each element in an iterator without
    modifying it in any way.

    This is useful for inspecting the results of an iterator.

    **Examples**

        :::python

        # Prints each element on it's own line
        it('abc').inspect(print).go()

        (it('abc')
            .inspect(lambda x: print('Before:', x))
            .map(lambda x: x.upper())
            .inspect(lambda x: print('After:', x))
            .go()
        )
    """
    def __init__(self, items, func):
        it.__init__(self, items)
        self.func = func

    def __get_next__(self):
        item = next(self.items)
        self.func(item)
        return item

    def __get_reversed__(self):
        return it(
            Inspect(self.reverse, self.func), self.items, self.size_hint()
        )


@trait('zip')
def zip_it(self, other):
    """
    Combines the elements from two iterators into a single iterator that returns
    tuples containing the elements of each.

    Discards elements of iterators longer than the other.

    **Examples**

        :::python

        assert it(range(2)).zip(range(1000)).collect() == [(0, 0), (1, 1)]
    """
    other_it = it(other)
    return it(
        zip(self, other_it),
        None if self.reverse is None else zip(self.reverse, reversed(other_it)),
        (
            self._lower_bound + other_it._lower_bound,
            self._upper_bound + other_it._upper_bound
        )
    )


@trait
def skip_while(self, closure):
    """
    Returns any element after each one that doesn't match the given function.

    **Examples**

        :::python

        assert (it('abDF')
            .skip_while(lambda x: x.upper() != x)
            .collect(str)
        ) == 'DF'
    """
    return it(
        itertools.dropwhile(closure, self), 
        None if self.reverse is None else itertools.dropwhile(closure, self.reverse), 
        (0, self._upper_bound)
    )


@trait
def flatten(self, preserve_strings=True, max_depth=1):
    """
    flattens and chains each element in the iterator, to `max_depth` levels.

    Args:
        preserve_strings (bool, optional): whether to keep strings intact instead of treating them as iterables. Defaults to True.
        max_depth (int, optional): what depth to stop at. Defaults to 1; pass None or inf for a full flatten.

    **Examples**

        :::python

        assert it([[[[[1]],[2]],[3]],[4]]).flatten(max_depth=None).collect()==[1,2,3,4]
    """
    if max_depth is None: max_depth = math.inf
    def deepflatten_generic(xs, depth=0):
        for x in xs:
            if isinstance(x, Iterable) and (preserve_strings or not isinstance(x, (str, bytes))) and (depth<max_depth):
                yield from deepflatten_generic(x, depth=depth+1)
            else:
                yield x
    return it(
        deepflatten_generic(self),
        deepflatten_generic(self.reverse),
        (self.size_hint()[0], None)
    )

@trait
def for_each(self, closure):
    """
    Iterator version of a `for` loop. Exactly the same as `map`.
    Executes `closure` on each element of `self`.

    **Examples**

        :::python

        # Prints each element on its own line.
        assert it('asdf').for_each(print)
    """
    return it(
        (closure(i) for i in self),
        (closure(i) for i in self.reverse),
        self.size_hint()
    )


@trait
def fold(self, seed, closure):
    """
    An iterator method that applies a function, producing a single, final value.

    `fold()` takes two arguments: an initial value, and a closure with two
    arguments: an 'accumulator', and an element. The closure returns the value
    that the accumulator should have for the next iteration.

    The initial value is the value the accumulator will have on the first call.

    After applying this closure to every element of the iterator, `fold()`
    returns the accumulator.

    This operation is sometimes called 'reduce' or 'inject'.

    Folding is useful whenever you have a collection of something, and want to
    produce a single value from it.

    See also: the builtin `operator` is often a useful shorthand here.

    **Examples**

        :::python

        assert it((1, 2, 3)).fold(1, lambda a, b: a*b) == 6
    """
    for i in self: seed = closure(seed, i)
    return seed


@trait
def scan(self, seed, closure):
    """
    An iterator adaptor similar to fold that holds internal state and produces a
    new iterator.

    `scan()` takes two arguments: an initial value which seeds the internal
    state, and a closure with two arguments, used to combine the elements of
    `self` one at a time. The closure plays the role of the `sum` operation 
    in `np.cumsum`.

    On iteration, the closure will be applied to each element of the iterator
    and the return value from the closure.

    **Examples**

        :::python

        assert (it((1, 2, 3))
            .scan(1, lambda a, b: a*b)
            .collect()
        ) == [1, 2, 6]
    """

    return it(
        itertools.accumulate(self, closure, initial=seed),
        None if self.reverse is None else itertools.accumulate(self.reverse, closure, initial=seed),
        self.size_hint()
    )



@trait
def par_iter(self):
    """
    Iterate through the elements of an iterator concurrently.

    Since CPython is only able to execute 1 true thread at a time, only the
    illusion of parallelism is achievable, which can definitely be highly useful
    in situations where tasks need to not execute sequencially.

    Please see [this talk](https://blog.golang.org/waza-talk) on why concurrency
    is not the same as parallelism.

    It should be noted that the name "par_iter" was taken from Rayon's
    [par_iter](https://docs.rs/rayon/0.6.0/rayon/par_iter/index.html) function.

    The order of items in the underlying iterator are maintained.

    If your item handling code has side-effects, `par_iter` may not be the best
    solution for you because it handles each item concurrently and those side
    effects may occur in a different order.

    **Examples**

    The order of the returned elements is maintained even though they are
    processed concurrently.

        :::python

        itr = it(range(3)).par_iter()
        assert itr.next() == 0
        assert itr.next() == 1
        assert itr.next() == 2

    Making HTTP requests is faster using `par_iter`:

        :::python
        from requests import get as GET

        urls = [...]

        results = (it(urls)
            .map(lambda u: GET(u))
            .map(lambda u: u.text if u.ok else u.reason)
            .par_iter()
            .collect()
        )
    """

    def _process_items(the_items):
        yield

        from concurrent.futures import ThreadPoolExecutor, as_completed, Future
        import multiprocessing

        num_cores = multiprocessing.cpu_count()

        pool = ThreadPoolExecutor(max_workers=num_cores)
        submitted = [None] * num_cores
        completed = False

        while not completed:
            for i in range(num_cores):
                submitted[i] = pool.submit(
                    lambda s, idx: (idx, next(s)), the_items, i
                )

            for value in as_completed(submitted):
                try:
                    index, val = value.result()
                    submitted[index] = val
                except StopIteration:
                    completed = True

            for value in submitted:
                if not isinstance(value, Future):
                    yield value


    # Prevent from continuing right off the bat by returning None initially.
    # E.g. subsequent calls to next() will yield actual values.
    forward = next(_process_items(self.items))
    backward = None if self.reversed is None else next(_process_items(self.rev()))

    return it(forward, backward, self.size_hint())


@trait
class Current(Peekable):
    """
    An iterator that lets you look at the current item in the iteration.

    Essentially holds onto the last item yielded from `next()`. Works like a
    call to `peek()` but for the current element.

    Extends `Peekable` to retain `next()`, `curr()`, and `peek()` methods.

    For the first element, `curr()` behaves exactly like `peek()`.

    **Examples**

        :::python

        c = it('asdf').current()
        assert c.curr() == 'a'
        assert c.peek() == 'a'
        assert c.next() == 'a'
        assert c.curr() == 'a'
        assert c.peek() == 's'
        assert c.next() == 's'
    """
    def __init__(self, items):
        Peekable.__init__(self, items)
        self.current_item = None

    def __next__(self):
        self.current_item = Peekable.__next__(self)
        return self.current_item

    def curr(self):
        if not self._modified:
            return self.peek()
        return self.current_item
