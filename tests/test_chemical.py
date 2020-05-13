from chemical import it


class MyItem:
    def __init__(self, val):
        self.val = val
    def __gt__(self, other):
        return self.val > other.val
    def __eq__(self, other):
        return self.val == other.val


def test_it():
    assert list(it(range(3))) == [0, 1, 2]
    assert list(it('abc')) == ['a', 'b', 'c']


def test_collect():
    assert it(range(3)).collect() == [0, 1, 2]
    assert it(range(3)).collect(tuple) == (0, 1, 2)
    assert it(range(3)).collect(set) == {0, 1, 2}
    class MyList(list): ...
    assert it(range(3)).collect(MyList) == MyList((0, 1, 2))


def test_skip():
    assert it(range(3)).skip(1).collect() == [1, 2]
    assert it(range(100)).skip(10).take(10).collect() == [*range(10, 20)]
    assert it(range(10)).skip(1).skip(1).collect() == [*range(2, 10)]


def test_peekable():
    xs = 1, 2, 3
    i = it(xs).peekable()

    assert i.peek() == xs[0]
    assert i.next() == xs[0]

    assert i.next() == xs[1]

    assert i.peek() == xs[2]
    assert i.peek() == xs[2]

    assert i.next() == xs[2]

def test_max():
    assert it((1, 2, 3, 4)).max() == 4
    assert it('asdf').max() == 's'
    assert it((MyItem(1), MyItem(2), MyItem(3))).max() == MyItem(3)


def test_min():
    assert it((1, 2, 3, 4)).min() == 1
    assert it('asdf').min() == 'a'
    assert it((MyItem(1), MyItem(2), MyItem(3))).min() == MyItem(1)


def test_chain():
    assert it((1, 2, 3)).chain((4, 5, 6)).collect() == [1, 2, 3, 4, 5, 6]
    assert it('as').chain((3.1, 2.4)).collect() == ['a', 's', 3.1, 2.4]


def test_filter():
    func = lambda x: x > 2; data = 1, 2, 3, 4, 5
    assert it(data).filter(func).collect() == list(filter(func, data))


def test_cycle():
    assert it(range(3)).cycle().take(6).collect() == [0, 1, 2, 0, 1, 2]
    assert it('abc').cycle().take(6).collect() == ['a', 'b', 'c', 'a', 'b', 'c']

