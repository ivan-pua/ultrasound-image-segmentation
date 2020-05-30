# All the "find best" functions are variations on the DP section of the algorithm
# find_best_path_jumping is the one currently used from typing import List
import pandas as pd


def find_best_path_jumping(curr):
    # get the globals
    # TODO try and remove this bc they slow down everything
    # global inv_prob  # doesn't change
    # global cost
    # global nexts
    df = pd.read_excel(r'/Users/puaqieshang/Desktop/test.xlsx', sheet_name='inv_prob')
    inv_prob = df.as_matrix()

    df = pd.read_excel(r'/Users/puaqieshang/Desktop/test.xlsx', sheet_name='cost')
    cost = df.as_matrix()

    df = pd.read_excel(r'/Users/puaqieshang/Desktop/test.xlsx', sheet_name='nexts')
    nexts = df.as_matrix()

    x = 306  # these are hardcoded - should be determined instead.
    y = 626

    # if at end
    if curr[1] is y:
        curr_cost = 0
        cost[curr[0]][curr[1]] = curr_cost
        nexts[curr[1]][curr[2]] = 0
        return

    max_jump = 50
    no_cells = max_jump * 2 + 1

    # create 2x1 array
    min_next = [0, 0]
    min_cost = float("inf")

    # calc costs
    for i in range(1, no_cells):
        # cell no
        next = curr + [i - max_jump - 1, 1]

        # out of bounds
        if next[0] < 1 or next[0] > x:
            next_cost = float("inf")

        # already calculated
        elif cost[next[0]][next[1]] != float("inf"):
            next_cost = cost[next[0]][next[1]]
            # print(next_cost)

        # need to recursively calculate
        else:
            next_cost = find_best_path_jumping(next)
            # print(next_cost)

        # add penalty if needed
        if abs(curr[0] - next[0]) > 2:
            next_cost = next_cost + 0.2

        # calculate running min
        if next_cost < min_cost:
            min_cost = next_cost
            min_next = next[0]

    # set results
    curr_cost = inv_prob(curr(0), curr(1)) + min_cost
    cost[curr[0], curr[1]] = curr_cost
    nexts[curr[0]][curr[1]] = min_next


find_best_path_jumping([1, 2, 3])  # test if its working
