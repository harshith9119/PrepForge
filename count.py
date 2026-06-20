import csv
from collections import Counter

def count_topics():
    # Mapping the IDs back to names so the output is readable
    topic_names = {
        '1': 'Basics',
        '2': 'Recursion / Strings',
        '3': 'Arrays / Sorting',
        '4': 'Binary Search',
        '5': 'Linked List',
        '6': 'Stack',
        '7': 'Queue',
        '8': 'Tree',
        '9': 'Graph',
        '10': 'Dynamic Programming (DP)'
    }

    try:
        with open('Prepforge_500_Fixed.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            # Count how many times each topic_id appears
            counts = Counter(row['topic_id'].strip() for row in reader if row.get('topic_id'))

        print("\n📊 Problem Count by Topic:")
        print("-" * 40)
        
        total = 0
        # Sort the results by topic ID numerically
        for topic_id in sorted(counts.keys(), key=lambda x: int(x) if x.isdigit() else 99):
            name = topic_names.get(topic_id, f"Topic {topic_id} (Other)")
            count = counts[topic_id]
            total += count
            print(f"{name:<25} | {count:>4} problems")
        
        print("-" * 40)
        print(f"{'TOTAL':<25} | {total:>4} problems\n")

    except FileNotFoundError:
        print("❌ Error: Could not find 'Prepforge_500_Fixed.csv'.")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == '__main__':
    count_topics()