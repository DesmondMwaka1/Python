
#Code implementation in Python
import heapq
import sys

def dijkstra(graph, start, end):  
    pq = [(0, start)] #stores distance and current node
    
    #shortest distance found so far to each node
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    
    # reconstruct the path
    predecessors = {node: None for node in graph}
    
    while pq:
        current_distance, u = heapq.heappop(pq)

        if current_distance > distances[u]:
            continue
            
        for v, weight in graph[u].items():
            distance = current_distance + weight

            if distance < distances[v]:
                distances[v] = distance
                predecessors[v] = u
                heapq.heappush(pq, (distance, v))
                
    # path from end to start
    path = []
    current = end
    
    # If the distance is still infinity, no path exists
    if distances[end] == float('inf'):
        return [], float('inf')
        
    while current is not None:
        path.append(current)
        current = predecessors[current]
        
    return path[::-1], distances[end]

# The graph 
graph = {
    0: {1: 4, 7: 8},
    1: {0: 4, 2: 8, 7: 11},
    2: {1: 8, 3: 7, 8: 2, 5: 4},
    3: {2: 7, 4: 9, 5: 14},
    4: {3: 9, 5: 10},
    5: {2: 4, 3: 14, 4: 10, 6: 2},
    6: {5: 2, 7: 1, 8: 6},
    7: {0: 8, 1: 11, 6: 1, 8: 7},
    8: {2: 2, 6: 6, 7: 7}
}

def main():
    start = 0
    target = 4
    
    path, total_distance = dijkstra(graph, start, target)
    
    print(f" Shortest Path Results from {start} to {target}")
    path = " -> ".join(map(str, path))
    print(f"Path: {path}")
    print(f"Total Distance: {total_distance}")

if __name__ == "__main__":
    main()
