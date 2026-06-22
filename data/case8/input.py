import random
import math
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import time
import sys
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

class Species:
    def __init__(self, name, initial_population, growth_rate, habitat_preference, 
                 migration_pattern, disease_susceptibility):
        self.name = name
        self.initial_population = initial_population
        self.current_population = initial_population
        self.growth_rate = growth_rate
        self.population_history = deque(maxlen=100)
        self.population_history.append(initial_population)
        self.habitat_preference = habitat_preference  # -1.0 to 1.0
        self.migration_rate = migration_pattern
        self.disease_resistance = 1 - disease_susceptibility
        self.extinction_risk = 0
        self.last_10_populations = [initial_population]*10
        self.adaptation_score = random.uniform(0.5, 1.5)
        self.genetic_diversity = random.uniform(0.3, 0.8)
        
    def update_population(self, interaction_effect, environmental_factor, step, 
                          habitat_quality, season_index):
        # Calculate population change with growth rate and interactions
        natural_change = self.current_population * self.growth_rate
        habitat_effect = self.habitat_preference * habitat_quality * 15
        seasonal_effect = self.calculate_seasonal_effect(season_index)
        
        combined_effect = (natural_change + interaction_effect + 
                           environmental_factor + habitat_effect + seasonal_effect)
        
        # Apply migration effects
        migration_change = self.current_population * self.migration_rate * (
            math.sin(step / 10) * 0.5 + 0.5
        )
        combined_effect += migration_change
        
        # Apply disease effects randomly
        if random.random() < 0.2:  # 20% chance of disease outbreak
            disease_impact = self.current_population * (1 - self.disease_resistance)
            combined_effect -= disease_impact
        
        # Genetic diversity effect
        genetic_effect = self.genetic_diversity * self.current_population * 0.1
        combined_effect += genetic_effect
        
        # Update population with constraints
        self.current_population = max(1, min(3000, int(combined_effect)))
        
        # Update population history and risk assessment
        self.population_history.append(self.current_population)
        self.update_extinction_risk()
        
    def calculate_seasonal_effect(self, season_index):
        # Different species respond differently to seasons
        season_effects = {
            0: lambda: self.current_population * 0.05,  # Spring
            1: lambda: self.current_population * -0.03,  # Summer
            2: lambda: self.current_population * 0.02,   # Autumn
            3: lambda: self.current_population * -0.04   # Winter
        }
        return season_effects.get(season_index % 4, lambda: 0)()
    
    def update_extinction_risk(self):
        # Calculate extinction risk based on population trends and stability
        self.last_10_populations.pop(0)
        self.last_10_populations.append(self.current_population)
        
        if len(self.last_10_populations) < 10:
            return
            
        recent_trend = sum(self.last_10_populations) / 10
        volatility = math.sqrt(sum((x - recent_trend)**2 for x in self.last_10_populations) / 10)
        
        if recent_trend < 15:
            self.extinction_risk = 5
        elif recent_trend < 40:
            self.extinction_risk = 4
        elif recent_trend < 80:
            self.extinction_risk = 3
        elif recent_trend < 150:
            self.extinction_risk = 2
        else:
            self.extinction_risk = 1
            
        # Adjust risk based on volatility
        self.extinction_risk = min(5, self.extinction_risk + int(volatility // 10))

    def get_population_trend(self):
        # Advanced trend analysis with 10-point window
        if len(self.population_history) < 10:
            return 'unknown'
        
        last_ten = list(self.population_history)[-10:]
        if all(x > y for x, y in zip(last_ten, last_ten[1:])):
            return 'increasing'
        elif all(x < y for x, y in zip(last_ten, last_ten[1:])):
            return 'decreasing'
        elif abs(max(last_ten) - min(last_ten)) < 15:
            return 'stable'
        else:
            return 'fluctuating'

class Environment:
    def __init__(self, num_species, habitat_diversity=5):
        self.species = []
        self.interaction_matrix = self.generate_interaction_matrix(num_species)
        self.environmental_factors = {
            'temperature': 0,
            'precipitation': 0,
            'nutrient_availability': 0,
            'habitat_quality': 0,
            'pollution_level': 0
        }
        self.seasonal_cycle = self.generate_seasonal_cycle()
        self.habitat_types = self.generate_habitats(habitat_diversity)
        self.current_season = 0
        
    def generate_interaction_matrix(self, num_species):
        # Create balanced interaction matrix with complex interactions
        matrix = []
        for _ in range(num_species):
            row = [random.choice([-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3]) 
                  for _ in range(num_species)]
            # Set diagonal to 0 (no self-interaction)
            row[random.randint(0, num_species-1)] = 0.0
            matrix.append(row)
        return matrix

    def generate_seasonal_cycle(self):
        # Create a 4-season cycle with varying effects
        seasons = []
        season_names = ['Spring', 'Summer', 'Autumn', 'Winter']
        season_effects = {
            'Spring': {'temperature': 1.0, 'precipitation': 1.5, 'nutrient': 1.2},
            'Summer': {'temperature': 1.2, 'precipitation': 0.8, 'nutrient': 0.9},
            'Autumn': {'temperature': 0.9, 'precipitation': 1.2, 'nutrient': 1.1},
            'Winter': {'temperature': 0.7, 'precipitation': 0.5, 'nutrient': 0.8}
        }
        
        for i in range(4):
            season = {
                'name': season_names[i],
                'temperature': random.uniform(-5.0, 5.0) * season_effects[season_names[i]]['temperature'],
                'precipitation': random.uniform(-4.0, 4.0) * season_effects[season_names[i]]['precipitation'],
                'nutrient_availability': random.uniform(-3.0, 3.0) * season_effects[season_names[i]]['nutrient'],
                'habitat_quality': random.uniform(-1.5, 1.5),
                'pollution_level': random.uniform(-1.0, 1.0)
            }
            seasons.append(season)
        return seasons

    def generate_habitats(self, num_habitats):
        # Generate diverse habitat types
        habitats = []
        habitat_names = ['Tropical Rainforest', 'Temperate Forest', 'Grassland', 
                         'Desert', 'Tundra', 'Freshwater', 'Marine', 'Coral Reef', 'Savanna']
        habitat_types = ['Forest', 'Grassland', 'Wetland', 'Mountain', 'Desert', 
                         'Tundra', 'Coastal', 'Urban', 'Agricultural']
        
        for _ in range(num_habitats):
            habitat = {
                'name': random.choice(habitat_names),
                'type': random.choice(habitat_types),
                'quality': random.uniform(0.4, 1.6),
                'capacity': random.randint(300, 5000),
                'fragmentation': random.uniform(0.1, 0.9)
            }
            habitats.append(habitat)
        return habitats

    def update_environmental_factors(self, step):
        # Cycle through seasons every 15 steps
        season_index = (step // 15) % 4
        self.current_season = season_index
        season = self.seasonal_cycle[season_index]
        
        # Add some random fluctuations to environmental factors
        fluctuations = {
            'temperature': random.uniform(-1.0, 1.0),
            'precipitation': random.uniform(-1.5, 1.5),
            'nutrient_availability': random.uniform(-1.0, 1.0),
            'habitat_quality': random.uniform(-0.5, 0.5),
            'pollution_level': random.uniform(-0.3, 0.3)
        }
        
        for factor, value in season.items():
            if factor != 'name':
                # Apply fluctuations but keep within reasonable bounds
                new_value = value + fluctuations[factor]
                # Clamp values to prevent extreme values
                if factor == 'temperature':
                    new_value = max(-10.0, min(10.0, new_value))
                elif factor == 'precipitation':
                    new_value = max(-5.0, min(5.0, new_value))
                self.environmental_factors[factor] = new_value
        
        return season['name']

class EcosystemSimulator:
    def __init__(self, num_species=12, max_steps=60):
        self.num_species = num_species
        self.max_steps = max_steps
        self.environment = Environment(num_species)
        self.species = self.initialize_species()
        self.setup_interactions()
        self.conservation_threshold = 25
        self.visualization_data = {
            'populations': [],
            'environment': [],
            'risk_levels': [],
            'biodiversity': []
        }
        self.simulation_start_time = time.time()
        self.biodiversity_index = 0
        
    def initialize_species(self):
        species = []
        habitat_preferences = [random.uniform(-1.0, 1.0) for _ in range(self.num_species)]
        migration_patterns = [random.uniform(0.01, 0.1) for _ in range(self.num_species)]
        disease_susceptibilities = [random.uniform(0.1, 0.4) for _ in range(self.num_species)]
        
        for i in range(self.num_species):
            name = f'Species_{i}' if i < 9 else f'Species_{i+1}'
            initial_pop = random.randint(20, 200)
            growth_rate = random.uniform(0.85, 1.15)
            species.append(Species(name, initial_pop, growth_rate, 
                                  habitat_preferences[i], migration_patterns[i], 
                                  disease_susceptibilities[i]))
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
                self.environment.environmental_factors['temperature'] * 1.5 +
                self.environment.environmental_factors['precipitation'] * 1.2 +
                self.environment.environmental_factors['nutrient_availability'] * 2.0 -
                self.environment.environmental_factors['pollution_level'] * 1.0
            )
            
            species.update_population(interaction_effect, environmental_effect, 
                                     step, habitat_quality, self.environment.current_season)
        
        # Store data for visualization
        self.store_visualization_data(step, current_season)
        
        # Update biodiversity index
        self.biodiversity_index = self.calculate_biodiversity_index()

    def store_visualization_data(self, step, season):
        # Store population data
        populations = [s.current_population for s in self.species]
        self.visualization_data['populations'].append(populations)
        
        # Store environmental data
        env_data = {
            'season': season,
            'temperature': self.environment.environmental_factors['temperature'],
            'precipitation': self.environment.environmental_factors['precipitation'],
            'nutrient': self.environment.environmental_factors['nutrient_availability'],
            'habitat_quality': self.environment.environmental_factors['habitat_quality'],
            'pollution': self.environment.environmental_factors['pollution_level']
        }
        self.visualization_data['environment'].append(env_data)
        
        # Store risk levels
        risk_levels = [s.extinction_risk for s in self.species]
        self.visualization_data['risk_levels'].append(risk_levels)
        
        # Store biodiversity data
        self.visualization_data['biodiversity'].append(self.biodiversity_index)

    def calculate_biodiversity_index(self):
        # Calculate biodiversity index based on genetic diversity and population distribution
        total_population = sum(s.current_population for s in self.species)
        if total_population == 0:
            return 0
            
        # Shannon diversity index
        entropy = 0
        for species in self.species:
            proportion = species.current_population / total_population
            if proportion > 0:
                entropy -= proportion * math.log(proportion, 10)
        
        # Simpson index
        simpson = 0
        for species in self.species:
            proportion = species.current_population / total_population
            simpson += proportion**2
        
        # Genetic diversity component
        avg_genetic_diversity = sum(s.genetic_diversity for s in self.species) / len(self.species)
        
        # Combined biodiversity index
        biodiversity = (entropy * 10 + (1 - simpson) * 10 + avg_genetic_diversity * 5) / 3
        return round(biodiversity, 2)

    def run_simulation(self):
        # Store initial state
        initial_total = sum(s.initial_population for s in self.species)
        initial_state = [(s.name, s.initial_population) for s in self.species]
        
        # Run simulation with progress bar
        print("\nRunning simulation steps...")
        for step in range(self.max_steps):
            # Update progress bar
            progress = (step + 1) / self.max_steps * 100
            bar = f"[{'=' * int(progress//2)}{' ' * (50 - int(progress//2))}]"
            print(f"\rStep {step+1}/{self.max_steps} | {bar} {progress:.1f}%", end="")
            
            # Simulate step
            self.simulate_step(step)
            
            # Add delay for visualization
            time.sleep(0.05)
        
        print("\n")
        
        # Get final state
        final_total = sum(s.current_population for s in self.species)
        final_state = [(s.name, s.current_population) for s in self.species]
        
        # Identify endangered species
        endangered = [s.name for s in self.species if s.current_population < self.conservation_threshold]
        
        return {
            'initial_total': initial_total,
            'final_total': final_total,
            'initial_state': initial_state,
            'final_state': final_state,
            'environmental_data': self.visualization_data,
            'endangered_species': endangered,
            'biodiversity_index': self.biodiversity_index
        }

    def generate_report(self, results):
        # Calculate key metrics
        dominant_species = max(self.species, key=lambda s: s.current_population)
        most_stable_species = min(self.species, key=lambda s: max(s.population_history))
        
        # Analyze population trends
        trends = {s.name: s.get_population_trend() for s in self.species}
        
        # Create detailed report with color coding
        report = []
        report.append("="*80)
        report.append(Fore.CYAN + "ADVANCED ECOSYSTEM SIMULATION REPORT")
        report.append("="*80)
        report.append(f"{Fore.GREEN}SIMULATED SPECIES: {self.num_species}")
        report.append(f"{Fore.GREEN}SIMULATION STEPS: {self.max_steps}")
        report.append(f"{Fore.YELLOW}BIODIVERSITY INDEX: {results['biodiversity_index']}")
        report.append("-"*80)
        
        # Population statistics
        report.append(f"{Fore.BLUE}INITIAL TOTAL POPULATION: {results['initial_total']}")
        report.append(f"{Fore.BLUE}FINAL TOTAL POPULATION: {results['final_total']}")
        report.append(f"{Fore.BLUE}NET POPULATION CHANGE: {results['final_total'] - results['initial_total']:+d}")
        
        # Dominant and stable species
        report.append("-"*80)
        report.append(f"{Fore.MAGENTA}DOMINANT SPECIES: {dominant_species.name} ({dominant_species.current_population} individuals)")
        report.append(f"{Fore.MAGENTA}MOST STABLE SPECIES: {most_stable_species.name} (Range: {min(most_stable_species.population_history)}-{max(most_stable_species.population_history)})")
        
        # Environmental conditions
        report.append("-"*80)
        report.append(Fore.CYAN + "ENVIRONMENTAL CONDITIONS OVERVIEW:")
        for i, env in enumerate(results['environmental_data']['environment']):
            season_color = [
                Fore.GREEN, Fore.YELLOW, Fore.RED, Fore.BLUE
            ][i % 4]
            report.append(f"  {season_color}Step {i+1}: {env['season']} - ")
            report.append(f"    {Fore.LIGHTBLUE_EX}Temp: {env['temperature']:.1f}°C, ")
            report.append(f"    {Fore.LIGHTBLUE_EX}Precip: {env['precipitation']:.1f}mm, ")
            report.append(f"    {Fore.LIGHTBLUE_EX}Nutrient: {env['nutrient']:.1f}")
        
        # Population trends and risk assessment
        report.append("-"*80)
        report.append(Fore.CYAN + "POPULATION TRENDS AND CONSERVATION STATUS:")
        for species, trend in trends.items():
            sp = next(s for s in self.species if s.name == species)
            risk_level = sp.extinction_risk
            risk_emoji = ['🟢', '🟡', '🟠', '🔴', '⚫'][risk_level-1] if risk_level > 0 else '⚪'
            risk_color = [
                Fore.GREEN, Fore.YELLOW, Fore.LIGHTRED_EX, Fore.RED, Fore.MAGENTA
            ][risk_level-1] if risk_level > 0 else Fore.LIGHTWHITE_EX
            
            report.append(f"  {risk_color}{species}: {trend} {risk_emoji} Risk Level: {risk_level} ")
            report.append(f"    Genetic Diversity: {sp.genetic_diversity:.2f} ")
            report.append(f"    Adaptation Score: {sp.adaptation_score:.2f}")
        
        # Endangered species
        report.append("-"*80)
        report.append(Fore.CYAN + "CONSERVATION STATUS:")
        if results['endangered_species']:
            endangered_list = ', '.join(results['endangered_species'])
            report.append(f"{Fore.RED}  CRITICAL: {endangered_list} (below {self.conservation_threshold} individuals)")
        else:
            report.append(f"{Fore.GREEN}  NO SPECIES BELOW CONSERVATION THRESHOLD")
        
        report.append("="*80)
        report.append(Fore.CYAN + "SIMULATION COMPLETE")
        report.append("="*80)
        
        return report

    def generate_visualizations(self):
        # Create comprehensive visualizations
        self.create_population_trends_plot()
        self.create_risk_levels_plot()
        self.create_biodiversity_plot()
        self.create_environmental_impact_plot()
        return (
            'population_trends.png', 
            'risk_levels.png', 
            'biodiversity.png',
            'environmental_impact.png'
        )

    def create_population_trends_plot(self):
        plt.figure(figsize=(14, 10))
        for i, species in enumerate(self.species):
            plt.plot(range(self.max_steps), 
                    [p[i] for p in self.visualization_data['populations']], 
                    label=species.name)
        plt.title('Population Trends Over Time', fontsize=16)
        plt.xlabel('Simulation Steps', fontsize=12)
        plt.ylabel('Population Count', fontsize=12)
        plt.legend()
        plt.grid(True)
        plt.savefig('population_trends.png')
        
    def create_risk_levels_plot(self):
        plt.figure(figsize=(14, 8))
        risk_data = np.array(self.visualization_data['risk_levels'])
        for i in range(len(self.species)):
            plt.plot(range(self.max_steps), 
                    [r[i] for r in self.visualization_data['risk_levels']], 
                    label=self.species[i].name)
        plt.yticks([1, 2, 3, 4, 5], ['Low', 'Moderate', 'High', 'Severe', 'Critical'])
        plt.title('Extinction Risk Levels Over Time', fontsize=16)
        plt.xlabel('Simulation Steps', fontsize=12)
        plt.ylabel('Risk Level', fontsize=12)
        plt.legend()
        plt.grid(True)
        plt.savefig('risk_levels.png')
        
    def create_biodiversity_plot(self):
        plt.figure(figsize=(14, 6))
        plt.plot(range(self.max_steps), 
                self.visualization_data['biodiversity'], 
                label='Biodiversity Index', color='green')
        plt.title('Biodiversity Index Over Time', fontsize=16)
        plt.xlabel('Simulation Steps', fontsize=12)
        plt.ylabel('Biodiversity Index', fontsize=12)
        plt.grid(True)
        plt.savefig('biodiversity.png')
        
    def create_environmental_impact_plot(self):
        plt.figure(figsize=(14, 10))
        env_data = self.visualization_data['environment']
        
        # Temperature plot
        plt.subplot(3, 2, 1)
        temperatures = [e['temperature'] for e in env_data]
        plt.plot(range(self.max_steps), temperatures, color='red')
        plt.title('Temperature Changes')
        plt.ylabel('Temperature (°C)')
        
        # Precipitation plot
        plt.subplot(3, 2, 2)
        precipitation = [e['precipitation'] for e in env_data]
        plt.plot(range(self.max_steps), precipitation, color='blue')
        plt.title('Precipitation Changes')
        plt.ylabel('Precipitation (mm)')
        
        # Nutrient availability plot
        plt.subplot(3, 2, 3)
        nutrient = [e['nutrient'] for e in env_data]
        plt.plot(range(self.max_steps), nutrient, color='green')
        plt.title('Nutrient Availability')
        plt.ylabel('Nutrient Index')
        
        # Habitat quality plot
        plt.subplot(3, 2, 4)
        habitat = [e['habitat_quality'] for e in env_data]
        plt.plot(range(self.max_steps), habitat, color='brown')
        plt.title('Habitat Quality')
        plt.ylabel('Habitat Quality Index')
        
        # Pollution plot
        plt.subplot(3, 2, 5)
        pollution = [e['pollution'] for e in env_data]
        plt.plot(range(self.max_steps), pollution, color='purple')
        plt.title('Pollution Levels')
        plt.ylabel('Pollution Index')
        
        plt.tight_layout()
        plt.savefig('environmental_impact.png')

def main():
    print(Fore.CYAN + "="*60)
    print(Fore.CYAN + "ADVANCED ECOSYSTEM SIMULATOR 3.0")
    print(Fore.CYAN + "="*60)
    print(Fore.WHITE + "This advanced simulation models a complex ecosystem with:")
    print(Fore.GREEN + "- Multiple species with unique characteristics and adaptations")
    print(Fore.GREEN + "- Seasonal environmental changes with random fluctuations")
    print(Fore.GREEN + "- Habitat preferences and migration patterns")
    print(Fore.GREEN + "- Disease outbreaks and extinction risk assessment")
    print(Fore.GREEN + "- Genetic diversity and adaptation scores")
    print(Fore.GREEN + "- Comprehensive biodiversity index calculation")
    print(Fore.GREEN + "- Detailed visualization of all simulation aspects")
    print(Fore.WHITE + "\nOUTPUT INCLUDES:")
    print(Fore.YELLOW + "- Comprehensive simulation report with color coding")
    print(Fore.YELLOW + "- Population trends graph")
    print(Fore.YELLOW + "- Extinction risk assessment")
    print(Fore.YELLOW + "- Biodiversity index tracking")
    print(Fore.YELLOW + "- Environmental impact visualization")
    print(Fore.YELLOW + "- Conservation status overview")
    print(Fore.WHITE + "-" * 60)
    
    # Configuration parameters
    num_species = 12
    simulation_steps = 60
    
    # Run simulation
    print(f"{Fore.GREEN}Initializing simulation with {num_species} species...")
    simulator = EcosystemSimulator(num_species=num_species, max_steps=simulation_steps)
    
    # Display simulation start time
    start_time = time.time()
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
    print(f"{Fore.CYAN}Simulation started at: {time_str}")
    
    results = simulator.run_simulation()
    
    # Generate and display report
    print(f"{Fore.CYAN}\nGenerating detailed simulation report...")
    report = simulator.generate_report(results)
    for line in report:
        print(line)
    
    # Generate and save visualizations
    print(f"{Fore.CYAN}\nGenerating comprehensive visualization graphs...")
    pop_file, risk_file, bio_file, env_file = simulator.generate_visualizations()
    print(f"{Fore.GREEN}Visualizations saved as:")
    print(f"  {Fore.YELLOW}{pop_file} (Population Trends)")
    print(f"  {Fore.YELLOW}{risk_file} (Risk Levels)")
    print(f"  {Fore.YELLOW}{bio_file} (Biodiversity Index)")
    print(f"  {Fore.YELLOW}{env_file} (Environmental Impact)")
    
    # Simple output of key metrics
    print(f"\n{Fore.CYAN}=== EXECUTION SUMMARY ===")
    print(f"{Fore.GREEN}TOTAL SPECIES SIMULATED: {num_species}")
    print(f"{Fore.GREEN}SIMULATION DURATION: {simulation_steps} STEPS")
    print(f"{Fore.GREEN}INITIAL POPULATION TOTAL: {results['initial_total']}")
    print(f"{Fore.GREEN}FINAL POPULATION TOTAL: {results['final_total']}")
    print(f"{Fore.GREEN}NET POPULATION CHANGE: {results['final_total'] - results['initial_total']:+d}")
    print(f"{Fore.GREEN}BIODIVERSITY INDEX: {results['biodiversity_index']}")
    print(f"{Fore.GREEN}ENDANGERED SPECIES COUNT: {len(results['endangered_species'])}")
    print(f"{Fore.GREEN}CONSERVATION WARNING: {'YES' if results['endangered_species'] else 'NO'}")
    
    # Calculate and display simulation duration
    duration = time.time() - start_time
    print(f"\n{Fore.CYAN}Simulation completed in {duration:.2f} seconds")
    print(f"{Fore.CYAN}Results generated at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")
    
    print(Fore.CYAN + "\n=== SIMULATION COMPLETE ===")
    print(Fore.GREEN + "Check your working directory for visualization files")
    print(Fore.CYAN + "="*60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{Fore.RED}Error occurred: {str(e)}")
        print(Fore.RED + "Please check the simulation parameters and try again")