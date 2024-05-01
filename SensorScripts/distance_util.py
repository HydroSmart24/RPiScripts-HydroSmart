from collections import Counter

def get_most_common_distances(distances):
    count = Counter(distances)

    #get the most common reoccured distance values within the time frame
    most_common = count.most_common(3)
    print("Most common distances:", most_common)

    total_distance = sum(dist for dist, _ in most_common)
    avg_distance = int(total_distance / 3)  #average of the most common occurred

    return avg_distance
