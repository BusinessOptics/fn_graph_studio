# FnGraph Studio

A visual studio for investigating fn_graph composers, light weight function pipelines for python.

See [fn_graph](https://github.com/BusinessOptics/fn_graph/) for more information.

## Installation

```
pip install fn_graph_studio
```

## Usage

If you don't know what fn_graph is you really do need to check it out at [fn_graph](https://github.com/BusinessOptics/fn_graph/).

Assuming you have a composer already built, create a python file.

```python
from fn_graph_studio import run_studio

# Assume you have a composer at this location
from .my_composer_module import my_composer

run_studio(my_composer)
```

then run the file. Then open your browser to [http://localhost:8050](http://localhost:8050).

## The interface

The interface allows the user to investigate the results of a query, as well as any intermediate results. It allows the user to navigate through the function graph either as a graph, or as a tree that is nested by namespace.

You can view both the result as well as the function definition that led to that result.

You can an expression over all the results, as well, which can be useful for filtering down to particular elements.

![Screenshot](./screenshot_graph.png)

### Navigator selector

The navigator selector (top left) allows you to select to view either the graph navigator or the tree navigator.

### Tree navigator

The tree navigator shows all the functions in the composer as a hierarchy nested by namespace. You can click on a function name to select it, and see the result or definition of the function.

### Graph navigator

The graph navigator allows you to directly visualize and navigate the function graph. You can click on a function node to select it, and see the result or definition of the function.

The **Filter** selector, along with the neighborhood size selector, will limit which nodes will be visible. This allows you to home in on just the important parts of the graph you are working on.

- **All**: Show all the functions in the graph
- **Ancestors**: Show the ancestors of the selectors node, up to **neighborhood size** levels away.
- **Descendants**: Show the descendants of the selectors node, up to **neighborhood size** levels away.
- **Neighbors**: Show any nodes that are a distance of **neighborhood size** away from the selected node.

The **Display** options control how the graph is displayed:

- **Flatten**: If selected this will not show namespaces as a hierarchical graph, but just show the full names directly in the node. This can be useful for looking as smaller parts of complicated graphs.
- **Parameters**: If selected this will show the parameter nodes. Hiding these can clean up the graph and make it easier to navigate.
- **Links**: If selected this will show graph links as full nodes, otherwise they as shows as small circles for clarities sake.
- **Caching**: This will show caching information. Nodes outlined in green will not be calculated at all, nodes outlined in orange will be pulled from cache, nodes outlined in red will be calculated.

### Selected function display

The function display selector (top right) controls whether the result of the selected function, or its definition will be shown.

The selected functions full name is and the result type is always shown.

### Result processor

You can process all the results of a query by using the result processor (bottom left). This will evaluate a python expression on the results and show the result of teh expression. You can use any python code. The incoming result is available as the result variable.

## Hot reloading

The FnGraph Studio take advantage of the hot reloading built into the dash framework. As such whenever you change any code the studio will reload and show the new result.

## Caching

It can be extremely useful to use the development cache with the studio, the development cache will store results to disk (so it will maintain through live reloading), and will invalidate the cache when functions are changed. To do this alter your studio python file to something like.

```python
from fn_graph_studio import run_studio

# Assume you have a composer at this location
from .my_composer_module import my_composer

run_studio(my_composer.development_cache(__name__))
```
