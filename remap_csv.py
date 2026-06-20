import csv
import sqlite3

def fix_csv_surgical():
    # 1. Fetch exact IDs from your database
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        topics = c.execute('SELECT id, name FROM topics').fetchall()
        conn.close()
    except Exception as e:
        print("❌ Could not connect to database.db.")
        return

    db_ids = {}
    for t_id, t_name in topics:
        name_lower = t_name.lower()
        if 'linked list' in name_lower: db_ids['list'] = str(t_id)
        elif 'queue' in name_lower: db_ids['queue'] = str(t_id)
        elif 'stack' in name_lower: db_ids['stack'] = str(t_id)
        elif 'tree' in name_lower: db_ids['tree'] = str(t_id)
        elif 'graph' in name_lower: db_ids['graph'] = str(t_id)
        elif 'dp' in name_lower or 'dynamic' in name_lower: db_ids['dp'] = str(t_id)

    # 2. Hyper-Specific Keyword Dictionaries
    keywords = {
        'list': ['list', 'node', 'lru', 'lfu', 'browser-history'],
        
        'tree': ['tree', 'bst', 'trie', 'ancestor', 'forest', 'root', 'leaf', 'path-sum', 'cameras'],
        
        'stack': ['stack', 'parentheses', 'polish', 'temperature', 'histogram', 'asteroid', 
                  'calculator', '132-pattern', 'remove-k-digits', 'decode-string', 'parser'],
        
        'queue': ['queue', 'sliding-window', 'stream', 'schedule', 'k-frequent', 'k-closest', 
                  'kth-largest', 'stone-weight', 'k-workers', 'smallest-range', 'median', 'dota2', 'cards'],
        
        'graph': ['graph', 'island', 'course', 'network', 'alien', 'flight', 'ladder', 'province', 
                  'bipartite', 'snake', 'region', 'bridge', 'building', 'component', 'water', 
                  'board', 'safe-state', 'redundant', 'rotting', 'word-search', 'division', 'itinerary', 'connect'],
        
        'dp': ['climb', 'coin', 'subsequence', 'robber', 'decode', 'jump', 'triangle', 'square', 
               'stock', 'envelope', 'word-break', 'interleav', 'edit-distance', 'balloon', 'regex', 
               'wildcard', 'uncrossed', 'arithmetic', 'fibonacci', 'partition', 'unique-path', 
               'min-path', 'target-sum', 'max-product']
    }

    input_file = 'Prepforge_500.csv' # MUST BE THE ORIGINAL FILE
    output_file = 'Prepforge_500_Fixed.csv'

    try:
        with open(input_file, mode='r', encoding='utf-8') as infile, \
             open(output_file, mode='w', newline='', encoding='utf-8') as outfile:

            # Clean duplicate header rows if they exist
            raw_lines = infile.readlines()
            cleaned_lines = [raw_lines[0]] 
            for line in raw_lines[1:]:
                if not line.startswith('topic_id'):
                    cleaned_lines.append(line)

            reader = csv.DictReader(cleaned_lines)
            writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                old_id = str(row['topic_id']).strip()
                url = str(row['url']).lower()
                new_id = old_id

                # Only re-route problems in the messed up batches (> 4)
                if old_id not in ['1', '2', '3', '4']:
                    matched = False
                    
                    # Check in specific order of priority
                    for category in ['tree', 'list', 'graph', 'stack', 'queue', 'dp']:
                        if any(word in url for word in keywords[category]):
                            new_id = db_ids.get(category, old_id)
                            matched = True
                            break
                    
                    # If it somehow STILL doesn't match anything, look at the old ID roughly
                    if not matched:
                        if old_id == '11': new_id = db_ids.get('graph', old_id) # 11 was mostly graph/list
                        elif old_id == '12': new_id = db_ids.get('dp', old_id)  # 12 was mostly DP/stack
                        elif old_id == '13': new_id = db_ids.get('queue', old_id) # 13 was mostly queues/heaps
                        else: new_id = db_ids.get('tree', old_id) 

                row['topic_id'] = new_id
                writer.writerow(row)

        print("✅ Success! The problems have been surgically sorted.")
        print("Run your count_topics.py script again to see the new, balanced numbers!")

    except FileNotFoundError:
        print(f"❌ Error: Could not find '{input_file}'. Please make sure your original CSV is here!")

if __name__ == '__main__':
    fix_csv_surgical()