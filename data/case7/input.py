import random
import math
import matplotlib.pyplot as plt
import numpy as np
from collections import deque

class Species:
    def __init__(self, name, initial_population, growth_rate, habitat_preference):
        self.name = name
        self.initial_population = initial_population
        self.current_population = initial_population
        self.growth_rate = growth_rate
        self.population_history = deque(maxlen=50)
        self.population_history.append(initial_population)
        self.habitat_preference = habitat_preference  # -1.0 to 1.0
        self.migration_rate = random.uniform(0.01, 0.08)
        self.disease_resistance = random.uniform(0.2, 0.5)
        self.extinction_risk = 0
        self.last_5_populations = [initial_population]*5
        
    def update_population(self, interaction_effect, environmental_factor, step, habitat_quality):
        # Calculate population change with growth rate and interactions
        natural_change = self.current_population * self.growth_rate
        habitat_effect = self.habitat_preference * habitat_quality * 10
        combined_effect = natural_change + interaction_effect + environmental_factor + habitat_effect
        
        # Apply migration effects every 10 steps
        if step % 10 == 0:
            migration_change = self.current_population * self.migration_rate * random.choice([-1, 1])
            combined_effect += migration_change
        
        # Apply disease effects randomly
        if random.random() < 0.15:  # 15% chance of disease outbreak
            disease_impact = self.current_population * (1 - self.disease_resistance)
            combined_effect -= disease_impact
        
        # Update population with constraints
        self.current_population = max(1, min(2000, int(combined_effect)))
        
        # Update population history and risk assessment
        self.population_history.append(self.current_population)
        self.update_extinction_risk()
        
    def update_extinction_risk(self):
        # Calculate extinction risk based on population trends
        self.last_5_populations.pop(0)
        self.last_5_populations.append(self.current_population)
        
        if len(self.last_5_populations) < 5:
            return
            
        recent_trend = sum(self.last_5_populations) / 5
        if recent_trend < 20:
            self.extinction_risk = 5
        elif recent_trend < 50:
            self.extinction_risk = 4
        elif recent_trend < 100:
            self.extinction_risk = 3
        elif recent_trend < 200:
            self.extinction_risk = 2
        else:
            self.extinction_risk = 1

    def get_population_trend(self):
        # Advanced trend analysis with 5-point window
        if len(self.population_history) < 5:
            return 'unknown'
        
        last_five = list(self.population_history)[-5:]
        if all(x > y for x, y in zip(last_five, last_five[1:])):
            return 'increasing'
        elif all(x < y for x, y in zip(last_five, last_five[1:])):
            return 'decreasing'
        elif abs(max(last_five) - min(last_five)) < 10:
            return 'stable'
        else:
            return 'fluctuating'

class Environment:
    def __init__(self, num_species, habitat_diversity=3):
        self.species = []
        self.interaction_matrix = self.generate_interaction_matrix(num_species)
        self.environmental_factors = {
            'temperature': 0,
            'precipitation': 0,
            'nutrient_availability': 0,
            'habitat_quality': 0
        }
        self.seasonal_cycle = self.generate_seasonal_cycle()
        self.habitat_types = self.generate_habitats(habitat_diversity)
        
    def generate_interaction_matrix(self, num_species):
        # Create balanced interaction matrix with mostly neutral interactions
        matrix = []
        for _ in range(num_species):
            row = [random.choice([-0.2, -0.1, 0.0, 0.1, 0.2]) for _ in range(num_species)]
            # Set diagonal to 0 (no self-interaction)
            row[random.randint(0, num_species-1)] = 0.0
            matrix.append(row)
        return matrix

    def generate_seasonal_cycle(self):
        # Create a 4-season cycle with varying effects
        seasons = []
        season_names = ['Spring', 'Summer', 'Autumn', 'Winter']
        for i in range(4):
            season = {
                'name': season_names[i],
                'temperature': random.uniform(-4.0, 4.0),
                'precipitation': random.uniform(-3.0, 3.0),
                'nutrient_availability': random.uniform(-2.0, 2.0),
                'habitat_quality': random.uniform(-1.0, 1.0)
            }
            seasons.append(season)
        return seasons

    def generate_habitats(self, num_habitats):
        # Generate diverse habitat types
        habitats = []
        habitat_names = ['Forest', 'Grassland', 'Wetland', 'Mountain', 'Desert', 'Tundra', 'Coastal']
        for _ in range(num_habitats):
            habitat = {
                'name': random.choice(habitat_names),
                'quality': random.uniform(0.5, 1.5),
                'capacity': random.randint(200, 1000)
            }
            habitats.append(habitat)
        return habitats

    def update_environmental_factors(self, step):
        # Cycle through seasons every 12 steps
        season_index = (step // 12) % 4
        season = self.seasonal_cycle[season_index]
        self.environmental_factors = season
        return season['name']

class EcosystemSimulator:
    def __init__(self, num_species=10, max_steps=50):
        self.num_species = num_species
        self.max_steps = max_steps
        self.environment = Environment(num_species)
        self.species = self.initialize_species()
        self.setup_interactions()
        self.conservation_threshold = 30
        self.visualization_data = {
            'populations': [],
            'environment': [],
            'risk_levels': []
        }
        
    def initialize_species(self):
        species = []
        habitat_preferences = [random.uniform(-1.0, 1.0) for _ in range(self.num_species)]
        for i in range(self.num_species):
            name = f'Species_{i}'
            initial_pop = random.randint(30, 150)
            growth_rate = random.uniform(0.92, 1.08)
            habitat_preference = habitat_preferences[i]
            species.append(Species(name, initial_pop, growth_rate, habitat_preference))
        return species

    def setup_interactions(self):
        # Link species interactions through the matrix
        for i, species in enumerate(self.species):
            species.interaction_weights = self.environment.interaction_matrix[i]

    def simulate_step(self, step):
        # Update environmental factors and get current season
        current_season = self.environment.update_environmental_factors(step)
        habitat_quality = self.environment.environmental_factors['habitat_quality']
        
        # Update each species population
        for i, species in enumerate(self.species):
            interaction_effect = sum(
                species.interaction_weights[j] * self.species[j].current_population
                for j in range(self.num_species)
            )
            
            environmental_effect = (
                self.environment.environmental_factors['temperature'] * 2 +
                self.environment.environmental_factors['precipitation'] * 1.5 +
                self.environment.environmental_factors['nutrient_availability'] * 3
            )
            
            species.update_population(interaction_effect, environmental_effect, step, habitat_quality)
        
        # Store data for visualization
        self.store_visualization_data(step, current_season)

    def store_visualization_data(self, step, season):
        # Store population data
        populations = [s.current_population for s in self.species]
        self.visualization_data['populations'].append(populations)
        
        # Store environmental data
        env_data = {
            'season': season,
            'temperature': self.environment.environmental_factors['temperature'],
            'precipitation': self.environment.environmental_factors['precipitation'],
            'nutrient': self.environment.environmental_factors['nutrient_availability']
        }
        self.visualization_data['environment'].append(env_data)
        
        # Store risk levels
        risk_levels = [s.extinction_risk for s in self.species]
        self.visualization_data['risk_levels'].append(risk_levels)

    def run_simulation(self):
        # Store initial state
        initial_total = sum(s.initial_population for s in self.species)
        initial_state = [(s.name, s.initial_population) for s in self.species]
        
        # Run simulation
        for step in range(self.max_steps):
            self.simulate_step(step)
        
        # Get final state
        final_total = sum(s.current_population for s in self.species)
        final_state = [(s.name, s.current_population) for s in self.species]
        
        # Identify endangered species
        endangered = [s.name for s in self.species if s.current_population < self.conservation_threshold]
        
        # Calculate biodiversity index
        biodiversity = len(set([s.current_population for s in self.species]))
        
        return {
            'initial_total': initial_total,
            'final_total': final_total,
            'initial_state': initial_state,
            'final_state': final_state,
            'environmental_data': self.visualization_data,
            'endangered_species': endangered,
            'biodiversity_index': biodiversity
        }

    def generate_report(self, results):
        # Calculate key metrics
        dominant_species = max(self.species, key=lambda s: s.current_population)
        most_stable_species = min(self.species, key=lambda s: max(s.population_history))
        
        # Analyze population trends
        trends = {s.name: s.get_population_trend() for s in self.species}
        
        # Create detailed report
        report = []
        report.append("="*60)
        report.append("ADVANCED ECOSYSTEM SIMULATION REPORT")
        report.append("="*60)
        report.append(f"SIMULATED SPECIES: {self.num_species}")
        report.append(f"SIMULATION STEPS: {self.max_steps}")
        report.append("-"*60)
        report.append(f"INITIAL TOTAL POPULATION: {results['initial_total']}")
        report.append(f"FINAL TOTAL POPULATION: {results['final_total']}")
        report.append(f"NET POPULATION CHANGE: {results['final_total'] - results['initial_total']:+d}")
        report.append(f"BIODIVERSITY INDEX: {results['biodiversity_index']}")
        report.append("-"*60)
        report.append(f"DOMINANT SPECIES: {dominant_species.name} ({dominant_species.current_population} individuals)")
        report.append(f"MOST STABLE SPECIES: {most_stable_species.name} (Range: {min(most_stable_species.population_history)}-{max(most_stable_species.population_history)})")
        report.append("-"*60)
        report.append("ENVIRONMENTAL CONDITIONS:")
        for i, env in enumerate(results['environmental_data']['environment']):
            report.append(f"  Step {i*5}: {env['season']} - Temp: {env['temperature']:.1f}°C, Precip: {env['precipitation']:.1f}mm, Nutrient: {env['nutrient']:.1f}")
        report.append("-"*60)
        report.append("POPULATION TRENDS:")
        for species, trend in trends.items():
            risk_level = next(s for s in self.species if s.name == species).extinction_risk
            risk_emoji = ['🟢', '🟡', '🟠', '🔴', '⚫'][risk_level-1] if risk_level > 0 else '⚪'
            report.append(f"  {species}: {trend} {risk_emoji} Risk Level: {risk_level}")
        report.append("-"*60)
        report.append("CONSERVATION STATUS:")
        if results['endangered_species']:
            report.append(f"  CRITICAL: {', '.join(results['endangered_species'])} (below {self.conservation_threshold} individuals)")
        else:
            report.append("  NO SPECIES BELOW CONSERVATION THRESHOLD")
        report.append("="*60)
        report.append("SIMULATION COMPLETE")
        report.append("="*60)
        
        return report

    def generate_visualizations(self):
        # Create population trends plot
        plt.figure(figsize=(12, 8))
        for i, species in enumerate(self.species):
            plt.plot(range(self.max_steps), 
                    [p[i] for p in self.visualization_data['populations']], 
                    label=species.name)
        plt.title('Population Trends Over Time')
        plt.xlabel('Simulation Steps')
        plt.ylabel('Population Count')
        plt.legend()
        plt.grid(True)
        plt.savefig('population_trends.png')
        
        # Create risk levels plot
        plt.figure(figsize=(12, 6))
        risk_data = np.array(self.visualization_data['risk_levels'])
        for i in range(len(self.species)):
            plt.plot(range(self.max_steps), 
                    [r[i] for r in self.visualization_data['risk_levels']], 
                    label=self.species[i].name)
        plt.title('Extinction Risk Levels Over Time')
        plt.xlabel('Simulation Steps')
        plt.ylabel('Risk Level (1-5)')
        plt.legend()
        plt.grid(True)
        plt.savefig('risk_levels.png')
        
        return 'population_trends.png', 'risk_levels.png'

def main():
    print("=== ADVANCED ECOSYSTEM SIMULATOR 2.0 ===\n")
    print("This advanced simulation models a complex ecosystem with:")
    print("- Multiple species with unique characteristics")
    print("- Seasonal environmental changes")
    print("- Habitat preferences and migration patterns")
    print("- Disease outbreaks and extinction risk assessment")
    print("- Detailed population trends visualization")
    print("\nOUTPUT INCLUDES:")
    print("- Comprehensive simulation report")
    print("- Population trends graph")
    print("- Extinction risk assessment")
    print("- Conservation status overview")
    print("-" * 60)
    
    # Configuration parameters
    num_species = 10
    simulation_steps = 50
    
    # Run simulation
    print(f"Initializing simulation with {num_species} species...")
    simulator = EcosystemSimulator(num_species=num_species, max_steps=simulation_steps)
    
    print("Running simulation steps...")
    results = simulator.run_simulation()
    
    # Generate and display report
    print("\nGenerating detailed simulation report...")
    report = simulator.generate_report(results)
    for line in report:
        print(line)
    
    # Generate and save visualizations
    print("\nGenerating visualization graphs...")
    pop_file, risk_file = simulator.generate_visualizations()
    print(f"Visualizations saved as: {pop_file} and {risk_file}")
    
    # Simple output of key metrics
    print("\n=== EXECUTION SUMMARY ===")
    print(f"TOTAL SPECIES SIMULATED: {num_species}")
    print(f"SIMULATION DURATION: {simulation_steps} STEPS")
    print(f"INITIAL POPULATION TOTAL: {results['initial_total']}")
    print(f"FINAL POPULATION TOTAL: {results['final_total']}")
    print(f"NET POPULATION CHANGE: {results['final_total'] - results['initial_total']:+d}")
    print(f"BIODIVERSITY INDEX: {results['biodiversity_index']}")
    print(f"ENDANGERED SPECIES COUNT: {len(results['endangered_species'])}")
    print(f"CONSERVATION WARNING: {'YES' if results['endangered_species'] else 'NO'}")
    
    print("\n=== SIMULATION COMPLETE ===")
    print("Check your working directory for visualization files")

if __name__ == "__main__":
    main()