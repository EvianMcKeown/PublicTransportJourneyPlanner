class Graph:
    def __init__(self, size):
      self.adjacency_matrix = [[0] * size for _ in range(size)]
      self.size = size
      self.vertex_data = [''] * size

    def add_edge(self, u, v, weight):
        if 0 <= u < self.size and 0 <= v < self.size:
            self.adjacency_matrix[u][v] = weight
            # weight would be time from u to v in our implementation

    def add_vertex_data(self, vertex, data):
        if 0 <= vertex < self.size:
            self.vertex_data[vertex] = data

    def dijkstra(self, start_vertex_data, end_vertex_data):
        start_vertex = self.vertex_data.index(start_vertex_data)
        end_vertex = self.vertex_data.index(end_vertex_data)
        distances = [float('inf')] * self.size #init distances as inf except for start_vertex
        predecessors = [None] * self.size  # fro storing shortest paths from origin to destinations
        distances[start_vertex] = 0
        visited = [False] * self.size #all vertices are initialised as 'not visited'

        for _ in range(self.size):
            min_distance = float('inf')
            u = None
            for i in range(self.size):
                if not visited[i] and distances[i] < min_distance:
                    min_distance = distances[i]
                    u = i

            if u is None or u == end_vertex:
                print(f"Breaking out of loop  -  Current vertex: {self.vertex_data[u]}")
                print(f"Distances: {distances}")
                break

            visited[u] = True
            
            for v in range(self.size):
                if self.adjacency_matrix[u][v] != 0 and not visited[v]:
                    alt = distances[u] + self.adjacency_matrix[u][v]
                    if alt < distances[v]:
                        distances[v] = alt
                        predecessors[v] = u
        
        return distances[end_vertex], self.get_path(predecessors, start_vertex_data, end_vertex_data)

    def get_path(self, predecessors, start_vertex, end_vertex):
        path = []
        current = self.vertex_data.index(end_vertex)
        while current is not None:
            path.insert(0, self.vertex_data[current])
            current = predecessors[current]
            if current == self.vertex_data.index(start_vertex):
                path.insert(0, start_vertex)
                break
        return '->'.join(path)  # vertices joined with ->
