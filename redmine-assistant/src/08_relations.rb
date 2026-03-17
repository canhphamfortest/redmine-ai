# /usr/src/redmine/init/08_relations.rb
# Create issue relations (blocks, relates, duplicates, precedes, follows)

RELATION_TYPES = %w[relates blocks duplicates precedes follows]

RELATION_PROB = {
  "relates" => 0.50,
  "blocks" => 0.15,
  "duplicates" => 0.10,
  "precedes" => 0.15,
  "follows" => 0.10
}

PRECEDES_DELAY_RANGE = 1..5  # days

# Helper function for weighted random selection
def pick_weighted_relation(hash)
  total = hash.values.map(&:to_f).sum
  r = rand * total
  acc = 0.0
  hash.each do |k, w|
    acc += w.to_f
    return k if r <= acc
  end
  hash.keys.last
end

def create_relations_for_pool(issue_pool, relation_count: 30)
  return if issue_pool.length < 2
  
  say "Creating relations for #{issue_pool.length} issues..."
  
  # Sample a subset to avoid too many relations
  pool = issue_pool.sample([issue_pool.length, 100].min)
  created = 0
  
  # Create relations between consecutive pairs
  pool.each_cons(2).first(relation_count).each do |issue_a, issue_b|
    type = pick_weighted_relation(RELATION_PROB)
    
    attrs = {
      issue_from: issue_a,
      issue_to: issue_b,
      relation_type: type
    }
    
    # Add delay for precedes relation
    attrs[:delay] = rand(PRECEDES_DELAY_RANGE) if type == 'precedes'
    
    begin
      # Check if relation already exists
      existing = IssueRelation.where(
        issue_from_id: issue_a.id,
        issue_to_id: issue_b.id
      ).first
      
      unless existing
        IssueRelation.create!(attrs)
        created += 1
      end
    rescue ActiveRecord::RecordInvalid => e
      # Ignore validation errors (e.g., circular dependencies)
    rescue => e
      warnx "Relation error: #{e.message}"
    end
  end
  
  # Create some random relations (not just consecutive)
  random_pairs = relation_count / 3
  random_pairs.times do
    issue_a = pool.sample
    issue_b = (pool - [issue_a]).sample
    next unless issue_b
    
    type = pick_weighted_relation(RELATION_PROB)
    
    attrs = {
      issue_from: issue_a,
      issue_to: issue_b,
      relation_type: type
    }
    
    attrs[:delay] = rand(PRECEDES_DELAY_RANGE) if type == 'precedes'
    
    begin
      existing = IssueRelation.where(
        issue_from_id: issue_a.id,
        issue_to_id: issue_b.id
      ).first
      
      unless existing
        IssueRelation.create!(attrs)
        created += 1
      end
    rescue
      # Ignore errors
    end
  end
  
  ok "Created #{created} relations"
end

# -------------------------
# Execute relations creation
# -------------------------

def generate_all_relations
  say "Generating issue relations..."
  
  ($projects_data || []).each do |data|
    project = data[:project]
    
    # Get recent issues from this project
    recent_issues = project.issues.order('id DESC').limit(80).to_a
    
    # Get some created issues if available
    created_in_project = ($all_created_issues || []).select { |i| i.project_id == project.id }
    
    pool = (recent_issues + created_in_project).uniq
    
    if pool.length >= 2
      create_relations_for_pool(pool, relation_count: [pool.length / 3, 50].min)
    else
      warnx "Not enough issues in #{project.identifier} to create relations"
    end
  end
  
  ok "All relations generated"
end

ok "Relations generator loaded"