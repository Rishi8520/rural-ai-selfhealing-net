import numpy as np
import asyncio # Import asyncio for async operations

class Salp:
    """Represents a single salp in the swarm, with its position (hyperparameters) and fitness."""
    def __init__(self, position, obj_func):
        self.position = np.array(position, dtype=np.float32)
        self.fitness = float('inf') # Initialize fitness to infinity
        self.obj_func = obj_func # Store the objective function for fitness evaluation

    async def evaluate_fitness(self):
        """Evaluates the fitness of this salp by calling the objective function asynchronously."""
        # The obj_func itself is async, so it needs to be awaited
        self.fitness = await self.obj_func(self.position)

class SalpSwarmOptimizer:
    """
    Implements the Salp Swarm Algorithm (SSA) for optimizing a given objective function.
    This optimizer is used to tune hyperparameters of the LSTM model in the Calculation Agent.
    """
    def __init__(self, obj_func, n_salps, n_iterations, lower_bounds, upper_bounds):
        """
        Initializes the Salp Swarm Optimizer.

        Args:
            obj_func (callable): The asynchronous objective function to minimize. It should take a numpy array
                                 of hyperparameters as input and return a single float (the fitness/loss).
            n_salps (int): The number of salps (population size) in the swarm.
            n_iterations (int): The maximum number of iterations for the optimization process.
            lower_bounds (list or np.array): A list or array of lower bounds for each hyperparameter.
            upper_bounds (list or np.array): A list or array of upper bounds for each hyperparameter.
        """
        self.obj_func = obj_func
        self.n_salps = n_salps
        self.n_iterations = n_iterations
        self.lower_bounds = np.array(lower_bounds, dtype=np.float32)
        self.upper_bounds = np.array(upper_bounds, dtype=np.float32)
        self.dim = len(lower_bounds) # Number of hyperparameters to optimize

        # Initialize salps randomly within bounds
        self.salps = [
            Salp(np.random.uniform(self.lower_bounds, self.upper_bounds), obj_func)
            for _ in range(n_salps)
        ]
        self.leader = None # The best salp found so far (will be initialized in optimize method)
        self.leader_fitness = float('inf') # The fitness of the best salp (will be initialized in optimize method)

    async def _get_best_salp(self):
        """
        Evaluates all salps and finds the one with the best fitness.
        This method is now asynchronous because it calls salp.evaluate_fitness().
        """
        # Concurrently evaluate fitness for all salps
        await asyncio.gather(*[salp.evaluate_fitness() for salp in self.salps])

        fitnesses = np.array([salp.fitness for salp in self.salps])
        best_idx = np.argmin(fitnesses)
        
        current_best_salp = self.salps[best_idx]

        # Update the global leader if a better salp is found
        if current_best_salp.fitness < self.leader_fitness:
            self.leader_fitness = current_best_salp.fitness
            # It's important to copy the position, not just reference it
            self.leader = Salp(current_best_salp.position.copy(), self.obj_func)
            self.leader.fitness = current_best_salp.fitness # Also copy the fitness


    def _update_position(self, salp_obj, salp_idx):
        """
        Updates the position of a salp based on leader or follower rules.
        Takes a Salp object directly to update its position.
        """
        if salp_idx == 0: # Leader salp
            # Eq. (3.1) for leader salp
            c1 = 2 * np.exp(-((4 * self.current_iter / self.n_iterations)**2))
            c2 = np.random.rand()
            c3 = np.random.rand()
            
            if c3 < 0.5:
                # Move towards the leader in a positive direction
                salp_obj.position = self.leader.position + c1 * ((self.upper_bounds - self.lower_bounds) * c2 + self.lower_bounds)
            else:
                # Move towards the leader in a negative direction
                salp_obj.position = self.leader.position - c1 * ((self.upper_bounds - self.lower_bounds) * c2 + self.lower_bounds)
        else: # Follower salps
            # Eq. (3.4) for follower salps
            # Follower position is the average of current salp and its preceding salp
            # Ensure index is valid for self.salps
            if salp_idx - 1 >= 0:
                salp_obj.position = (salp_obj.position + self.salps[salp_idx-1].position) / 2
            else:
                # This case should ideally not happen if loop starts from i=0
                pass 

        # Keep salps within bounds after updating position
        salp_obj.position = np.clip(salp_obj.position, self.lower_bounds, self.upper_bounds)


    async def optimize(self):
        """
        Runs the Salp Swarm Optimization algorithm to find the best hyperparameters.
        The algorithm iteratively updates salp positions based on the leader's position.
        This method is now asynchronous as it involves awaiting fitness evaluations.
        """
        print(f"SSA Optimization started with {self.n_salps} salps for {self.n_iterations} iterations.")
        
        # Initialize leader by evaluating all salps for the first time
        await self._get_best_salp() # This evaluates all initial salps and sets self.leader

        for self.current_iter in range(self.n_iterations):
            # Update positions of leader and follower salps
            for i, salp in enumerate(self.salps):
                self._update_position(salp, i) # Pass salp object and its index

            # Evaluate fitness of all salps after position updates
            await self._get_best_salp() # This re-evaluates all salps and updates the leader

            print(f"SSA Iteration {self.current_iter + 1}/{self.n_iterations}, Current Best Fitness: {self.leader_fitness:.4f}")
        
        print(f"SSA Optimization finished. Final Best Fitness: {self.leader_fitness:.4f}")
        return self.leader.position, self.leader_fitness

if __name__ == "__main__":
    # Example usage: Minimize the Sphere function (a common test function)
    # F(x) = sum(x^2)
    async def sphere_function(x):
        """An asynchronous version of the Sphere function."""
        await asyncio.sleep(0.001) # Simulate some async work
        return np.sum(x**2)

    lower_bounds = [-5.12, -5.12]
    upper_bounds = [5.12, 5.12]

    # Run the optimizer
    ssa = SalpSwarmOptimizer(
        obj_func=sphere_function,
        n_salps=10,
        n_iterations=50,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds
    )

    print("Starting SSA optimization for Sphere function...")
    # asyncio.run() is used to run the top-level async function
    best_params, best_fitness = asyncio.run(ssa.optimize())

    print(f"\nOptimization complete for Sphere function:")
    print(f"Best Parameters: {best_params}")
    print(f"Best Fitness (Minimum Value): {best_fitness}")