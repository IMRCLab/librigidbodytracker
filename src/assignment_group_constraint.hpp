#pragma once

#include <boost/bimap.hpp>
#include <boost/graph/adjacency_list.hpp>
// #include <boost/graph/find_flow_cost.hpp>
#include <boost/graph/successive_shortest_path_nonnegative_weights.hpp>

namespace libMultiRobotPlanning {

/*!
  \example assignment.cpp example that takes cost mappings from a file
*/

/*! \brief Find optimal (lowest total cost) assignment

This class can find the lowest sum-of-cost assignment
for given agents and tasks. The costs must be integers, the agents and
tasks can be of any user-specified type.

This method is based on maximum flow formulation.

\tparam Agent Type of the agent. Needs to be copy'able and comparable
\tparam Task Type of task. Needs to be copy'able and comparable
*/
template <typename Agent, typename Task>
class Assignment {
 public:
  Assignment()
      : m_agents(), m_tasks(), m_graph(), m_sourceVertex(), m_sinkVertex() {
    m_sourceVertex = boost::add_vertex(m_graph);
    m_sinkVertex = boost::add_vertex(m_graph);
  }

  void clear() {
    // std::cout << "Asg: clear" << std::endl;
    std::set<edge_t> edgesToRemove;
    for (const auto& agent : m_agents) {
      auto es = boost::out_edges(agent.right, m_graph);
      for (auto eit = es.first; eit != es.second; ++eit) {
        if (!m_graph[*eit].isReverseEdge) {
          edgesToRemove.insert(*eit);
          edgesToRemove.insert(m_graph[*eit].reverseEdge);
        }
      }
    }

    for (const auto& e : edgesToRemove) {
      boost::remove_edge(e, m_graph);
    }
  }

  void setCost(const Agent& agent, const std::set<Task>& group, long cost) {
    std::cout << "setCost: " << agent << "->" << "group";
    for (std::string task : group) {
        std::cout << task << " ";
    }
    std::cout <<" cost: " << cost << std::endl; 

    // Lazily create vertex for agent
    auto agentIter = m_agents.left.find(agent);
    vertex_t agentVertex;
    if (agentIter == m_agents.left.end()) {
      agentVertex = boost::add_vertex(m_graph);
      // std::cout << "outside addOrUpdateEdge(m_sourceVertex, agentVertex, 0,1); "<< std::endl;
      // addOrUpdateEdge(m_sourceVertex, agentVertex, 0, 2);
      m_agents.insert(agentsMapEntry_t(agent, agentVertex));
    } else {
      agentVertex = agentIter->second;
    }

    // Lazily create vertex for group
    auto groupIter = m_groups.find(group);
    vertex_t groupVertex;
    if (groupIter == m_groups.end()) {
      groupVertex = boost::add_vertex(m_graph);
      std::cout << "Group size: " << group.size() << std::endl;
      // addOrUpdateEdge(agentVertex, groupVertex, cost,group.size());
      m_groups.insert(groupsMapEntry_t(group, groupVertex));
    }else {
      groupVertex = groupIter->second;
    }
    addOrUpdateEdge(agentVertex, groupVertex, cost,group.size());
    // TODO: find the max of group.size() and current capacity value  ???
    // auto e = boost::edge(m_sourceVertex, agentVertex, m_graph);
    // m_graph[e.first].capacity;
    // addOrUpdateEdge(m_sourceVertex, agentVertex, 0, 2);


    // Lazily create vertex for tasks
    // add a for loop over group
    for (const auto& task : group) {
      auto taskIter = m_tasks.left.find(task);
      vertex_t taskVertex;
      if (taskIter == m_tasks.left.end()) {
        taskVertex = boost::add_vertex(m_graph);
        addOrUpdateEdge(taskVertex, m_sinkVertex, 0,1);
        m_tasks.insert(tasksMapEntry_t(task, taskVertex));
      } else {
        taskVertex = taskIter->second;
      }
      addOrUpdateEdge(groupVertex,taskVertex, 0,1);

    }
    std::cout << "---- end one setCost ----" << std::endl;

  }

  // find first (optimal) solution with minimal cost
  long solve(std::map<Agent,std::set<Task>>& solution) {
    using namespace boost;

    int max_capacity = 0;
    for (const auto& agent : m_agents) {
      // int max_capacity = 0;
      for (const auto& group : m_groups) {
        auto e = boost::edge(agent.right, group.second, m_graph);
        if (e.second) {
          std::cout << "Agent: " << agent.left
                    << " Group: "; 
          for (const auto& task : group.first) {
            std::cout << task << " ";
          }
          std::cout << " m_graph[e.first].capacity: " << m_graph[e.first].capacity << std::endl;
          if (m_graph[e.first].capacity > max_capacity){max_capacity = m_graph[e.first].capacity;}
        }
      }
      // std::cout << "Max Capacity: " << max_capacity << std::endl;
      // addOrUpdateEdge(m_sourceVertex, agent.right, 0, max_capacity);
    }
    std::cout << "Max Capacity: " << max_capacity << std::endl;

    for (const auto& agent : m_agents) {
      addOrUpdateEdge(m_sourceVertex, agent.right, 0, max_capacity);
    }

    // auto e = boost::edge(agentVertex, groupVertex, m_graph);
    // m_graph[e.first].capacity;

    successive_shortest_path_nonnegative_weights(
        m_graph, m_sourceVertex, m_sinkVertex,
        boost::capacity_map(get(&Edge::capacity, m_graph))
            .residual_capacity_map(get(&Edge::residualCapacity, m_graph))
            .weight_map(get(&Edge::cost, m_graph))
            .reverse_edge_map(get(&Edge::reverseEdge, m_graph)));

    long cost = 0;

    // find solution
    solution.clear();

    auto es = out_edges(m_sourceVertex, m_graph);
    for (auto eit = es.first; eit != es.second; ++eit) {
      std::cout << "rC " << m_graph[*eit].residualCapacity << std::endl;
      vertex_t agentVertex = target(*eit, m_graph);
      auto es2 = out_edges(agentVertex, m_graph);
      for (auto eit2 = es2.first; eit2 != es2.second; ++eit2) {
        if (!m_graph[*eit2].isReverseEdge) {
          vertex_t groupVertex = target(*eit2, m_graph);
          std::cout << "rC2 " << m_graph[*eit2].residualCapacity << std::endl;

          if (m_graph[*eit2].residualCapacity == 0) {    // residual = max - real   residual==0 means maxflow now
          //if (false) {
            for (auto itr = m_groups.begin(); itr != m_groups.end(); ++itr) {
                if (itr->second == groupVertex) {
                    std::set<Task> correspondingGroup = itr->first;
                    solution[m_agents.right.at(agentVertex)] =
                        correspondingGroup;    
                    for (const auto& element : itr->first) {
                        std::cout << element << " ";
                    }                
                    std::cout << std::endl;
                    // std::cout << "Key found: " << itr->first << std::endl;
                    break;

                }
            }

            // solution[m_agents.right.at(agentVertex)] =
            //     m_groups.at(groupVertex);    // m_groups cannot use .right.at  need to search in the google 
                // on .right.at in boost::bimap, find function same in std::map<std::set<Task>
                // what():  bimap<>: invalid key

            // cost += m_graph[edge(agentVertex, taskVertex, m_graph).first].cost;
            cost += m_graph[edge(agentVertex, groupVertex, m_graph).first].cost;  // Is this right?
            break;
          }
        }
      }
    }

    return cost;
  }

 protected:
  typedef boost::adjacency_list_traits<boost::vecS, boost::vecS,
                                       boost::bidirectionalS>
      graphTraits_t;
  typedef graphTraits_t::vertex_descriptor vertex_t;
  typedef graphTraits_t::edge_descriptor edge_t;

  struct Vertex {
    // boost::default_color_type color;
    // edge_t predecessor;
  };

  struct Edge {
    Edge()
        : cost(0),
          capacity(0),
          residualCapacity(0),
          reverseEdge(),
          isReverseEdge(false) {}

    long cost;
    long capacity;
    long residualCapacity;
    edge_t reverseEdge;
    bool isReverseEdge;
  };

  typedef boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS,
                                Vertex, Edge>
      graph_t;

 protected:
  void addOrUpdateEdge(vertex_t from, vertex_t to, long cost, long capacity) {
    // check if there is an edge in graph
    auto e = boost::edge(from, to, m_graph);
    if (e.second) {
      std::cout << "!!!!found edge ->"<<"old "<<m_graph[e.first].cost<<" update cost "<<cost << std::endl; 
      // found edge -> update cost
      m_graph[e.first].cost = cost;
      m_graph[m_graph[e.first].reverseEdge].cost = -cost;
      // TODO -> update capacity
      m_graph[e.first].capacity = capacity;
    } else {
      // no edge in graph yet
      auto e1 = boost::add_edge(from, to, m_graph);
      m_graph[e1.first].cost = cost;
      m_graph[e1.first].capacity = capacity;
      std::cout << "Capacity: " << m_graph[e1.first].capacity << ", Cost: " << m_graph[e1.first].cost << std::endl; // Print the capacity and cost
      auto e2 = boost::add_edge(to, from, m_graph);
      m_graph[e2.first].isReverseEdge = true;
      m_graph[e2.first].cost = -cost;
      m_graph[e2.first].capacity = 0;
      m_graph[e1.first].reverseEdge = e2.first;
      m_graph[e2.first].reverseEdge = e1.first;
    }

  }


 private:
  typedef boost::bimap<Agent, vertex_t> agentsMap_t;
  typedef typename agentsMap_t::value_type agentsMapEntry_t;
  typedef boost::bimap<Task, vertex_t> tasksMap_t;
  typedef typename tasksMap_t::value_type tasksMapEntry_t;

  agentsMap_t m_agents;
  tasksMap_t m_tasks;

  typedef std::map<std::set<Task>, vertex_t> groupsMap_t;
  typedef typename groupsMap_t::value_type groupsMapEntry_t;
  groupsMap_t m_groups;
  

  graph_t m_graph;
  vertex_t m_sourceVertex;
  vertex_t m_sinkVertex;
};

}  // namespace libMultiRobotPlanning
