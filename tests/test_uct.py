__author__ = 'johannes'

import pytest
import random

from mcts.graph import (depth_first_search, get_actions_and_states, StateNode)
from mcts.mcts import *
from mcts.utils import rand_max
from mcts.tree_policies import ucb1
from mcts.states.toy_world_state import *


parametrize_gamma = pytest.mark.parametrize("gamma",
                                            [.1, .2, .3, .4, .5, .6, .7, .8,
                                             .9])

parametrize_n = pytest.mark.parametrize("n", [1, 10, 23, 100, 101])


@pytest.fixture
def eps():
    return 10e-3


class UCBTestState(object):
    def __init__(self, id=0):
        self.actions = [0]
        self.hash = id

    def perform(self, action):
        return UCBTestState(self.hash+1)

    def is_terminal(self):
        return False

    def reward(self, parent, action):
        return -1

    def __hash__(self):
        return self.hash

    def __eq__(self, other):
        return self.hash == other.hash


def test_ucb1():
    parent = StateNode(None, UCBTestState(), 0)
    an = parent.children[0]

    an.n = 1
    parent.n = 1
    assert ucb1(an, parent, 1) == 0
    ucb = functools.partial(ucb1, parent=parent, c=1)
    ucb_1 = functools.partial(ucb1, parent=parent, c=1)
    assert ucb(an) == 0
    assert ucb_1(an) == 0

    an.n = 0
    parent.n = 1
    assert np.isnan(ucb1(an, parent, 1))
    ucb = functools.partial(ucb1, parent=parent, c=1)
    assert np.isnan(ucb(an))
    assert np.isnan(ucb_1(an))

    an.n = 1
    parent.n = 0
    assert np.isnan(ucb1(an, parent, 1))
    ucb = functools.partial(ucb1, parent=parent, c=1)
    assert np.isnan(ucb(an))
    assert np.isnan(ucb_1(an))

    an.q = 1
    an.n = 1
    parent.n = 1
    assert ucb1(an, parent, 1) == 1
    ucb = functools.partial(ucb1, parent=parent, c=1)
    assert ucb(an) == 1
    assert ucb_1(an) == 1

    an.q = 19
    an.n = 0
    assert ucb1(an, parent, 0) == 19


class ComplexTestState(object):
    def __init__(self, name):
        self.actions = [ComplexTestAction('a'), ComplexTestAction('b')]
        self.name = name

    def perform(self, action):
        return ComplexTestState(action.name)

    def is_terminal(self):
        return False

    def reward(self, parent, action):
        return -1

    def __hash__(self):
        return self.name.__hash__()

    def __eq__(self, other):
        return self.name == other.name


class ComplexTestAction(object):
    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return self.name.__hash__()

    def __eq__(self, other):
        return self.name == other.name


def test_best_child():
    parent = StateNode(None, ComplexTestState('root'), 0)
    an0 = parent.children[ComplexTestAction('a')]
    an1 = parent.children[ComplexTestAction('b')]

    an0.q = 2
    an0.n = 1
    an1.q = 1
    an1.n = 1

    assert len(parent.children.values()) == 2

    assert best_child(parent, 0).state.name == 'a'


def test_rand_max():
    i = [1, 4, 5, 3]
    assert rand_max(i) == 5

    i = [1, -5, 3, 2]
    assert rand_max(i, key=lambda x:x**2) == -5

    parent = StateNode(None, ComplexTestState('root'), 0)
    an0 = parent.children[ComplexTestAction('a')]
    an1 = parent.children[ComplexTestAction('b')]

    an0.q = 2
    an0.n = 1
    an1.q = 1
    an1.n = 1

    ucb = functools.partial(ucb1, parent=parent, c=0)
    assert rand_max(parent.children.values(),
                              lambda x: x.q).action.name == 'a'

    assert rand_max(parent.children.values(),
                              ucb).action.name == 'a'


def test_untried_actions():
    s = ComplexTestState('root')
    sn = StateNode(None, s, 0)
    assert ComplexTestAction('a') in sn.untried_actions
    assert ComplexTestAction('b') in sn.untried_actions

    sn.children[ComplexTestAction('a')].n = 1
    assert ComplexTestAction('a') not in sn.untried_actions
    assert ComplexTestAction('b') in sn.untried_actions


def test_sample_state():
    s = ComplexTestState('root')
    root = StateNode(None, s, 0)

    child = root.children[ComplexTestAction('a')]
    child.sample_state()

    assert len(child.children.values()) == 1
    assert ComplexTestState('a') in child.children

    child.sample_state()
    assert len(child.children.values()) == 1
    assert ComplexTestState('a') in child.children


@pytest.fixture
def toy_world_root():
    world = ToyWorld((100, 100), False, (10, 10), np.array([100, 100]))
    state = ToyWorldState((0, 0), world)
    root = StateNode(None, state, 0)
    return root, state


@parametrize_gamma
def test_single_run_uct_search(toy_world_root, gamma):
    root, state = toy_world_root
    random.seed()

    best_child = mcts_search(root=root, gamma=gamma, n=1)

    states = [state for states in [action.children.values()
                                   for action in root.children.values()]
              for state in states]

    assert len(states) == 2

    assert (len(list(root.children[best_child].children.values())) == 1)

    expanded = None
    for action in root.children.values():
        if (action.action != best_child and
                len(list(action.children.values())) == 1):
            assert expanded is None
            expanded = action

    for state in states:
        assert (np.sum(np.array(list(state.state.belief.values()))) - 1 ==
                np.sum(np.array(list(root.state.belief.values()))))
    assert root.n == 1

    for action in root.children.values():
        if action.action == expanded.action:
            assert action.q == -1.0
        else:
            assert action.q == 0.0


@parametrize_gamma
@parametrize_n
def test_n_run_uct_search(toy_world_root, gamma, n):
    root, state = toy_world_root
    random.seed()

    mcts_search(root=root, gamma=gamma, n=n)

    assert root.n == n

    action_nodes, state_nodes = depth_first_search(root,
                                                   get_actions_and_states)

    for action in action_nodes:
        assert action.n == np.sum([state.n
                                   for state in action.children.values()])

    for state in state_nodes:
        assert state.n >= np.sum([action.n
                                  for action
                                  in state.children.values()]) >= state.n - 1
        if state.parent is not None:
            assert (np.array(list(state.state.belief.values())).sum() - 1 ==
                    np.array(list(state.parent.parent.state.belief.values())).
                    sum())


@parametrize_gamma
def test_q_value_simple_state(gamma, eps):
    root = StateNode(None, UCBTestState(0), 0)
    mcts_search(root, gamma=gamma, n=350, c=2)
    assert root.q - (-1./(1 - gamma)) < eps


@parametrize_gamma
def test_q_value_complex_state(gamma, eps):
    if gamma > 0.5:  # with bigger gamma UCT converges too slow
        return
    root = StateNode(None, ComplexTestState(0), 0)
    mcts_search(root, gamma=gamma, n=1500, c=2)
    assert root.q - (-1./(1 - gamma)) < eps
