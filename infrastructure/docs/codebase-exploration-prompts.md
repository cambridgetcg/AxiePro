# Codebase Exploration Prompts Guide

A curated collection of prompts and techniques for deep codebase understanding, architectural analysis, and systematic debugging.

---

## 1. Initial Codebase Orientation

### High-Level Architecture Discovery
```
What is the overall architecture of this codebase? Identify:
- Entry points (main files, app initialization)
- Core modules and their responsibilities
- Data flow between components
- External dependencies and integrations
```

### Project Structure Analysis
```
Analyze the directory structure and explain:
- How is code organized (by feature, by layer, by domain)?
- Where are configuration files located?
- What build/deployment tooling is used?
- What testing patterns are employed?
```

### Technology Stack Identification
```
Identify all technologies, frameworks, and tools used:
- Programming languages and versions
- Frameworks and their configurations
- Database systems and ORMs
- Infrastructure as Code tools
- CI/CD pipelines
```

---

## 2. Deep Dive Explorations

### Dependency Chain Analysis
```
Trace the dependency chain for [component/module]:
- What does it import/depend on?
- What depends on it (reverse dependencies)?
- Are there any circular dependencies?
- What would break if this component changed?
```

### Data Flow Tracing
```
Trace how data flows from [input point] to [output point]:
- Entry validation and transformation
- Business logic processing steps
- Database interactions
- Response formatting
- Error handling at each stage
```

### Configuration Propagation
```
How does configuration propagate through the system?
- Environment variable loading
- Config file parsing
- Default value fallbacks
- Runtime vs build-time config
- Secrets management
```

---

## 3. Debugging & Troubleshooting

### Error Root Cause Analysis
```
Given this error: [error message]
1. What component generated it?
2. What are possible root causes?
3. What upstream conditions could trigger this?
4. What's the fix, and are there side effects?
```

### Startup Sequence Analysis
```
What happens when the application starts?
- Module import order and side effects
- Connection establishment (DB, cache, queues)
- Configuration validation
- Health check requirements
- Graceful degradation if dependencies unavailable
```

### Connection Lifecycle
```
Analyze the [database/cache/API] connection lifecycle:
- When is the connection established?
- How is connection pooling handled?
- What happens on connection failure?
- How are credentials managed and rotated?
```

---

## 4. Security & Performance

### Authentication Flow Mapping
```
Map the complete authentication flow:
- Credential submission
- Validation and token generation
- Token storage and transmission
- Session management
- Permission/role checks at each endpoint
```

### Performance Bottleneck Identification
```
Identify potential performance bottlenecks:
- N+1 query patterns
- Unbounded data fetches
- Missing indexes
- Synchronous blocking in async code
- Memory leaks in long-running processes
```

### Security Surface Analysis
```
Analyze the attack surface:
- Input validation points
- SQL/NoSQL injection vectors
- XSS vulnerabilities
- Authentication bypass possibilities
- Secrets exposure risks
```

---

## 5. Infrastructure & Deployment

### Infrastructure Dependency Mapping
```
Map all infrastructure dependencies:
- Compute resources (containers, serverless, VMs)
- Data stores (relational, document, cache)
- Message queues and event streams
- External APIs and services
- DNS and load balancing
```

### Environment Parity Analysis
```
Compare environments (dev/staging/prod):
- Configuration differences
- Resource sizing variations
- Feature flags per environment
- Data isolation strategies
- Deployment pipelines
```

### Failure Mode Analysis
```
What happens when [component] fails?
- Immediate impact
- Cascade effects
- Recovery mechanisms
- Data consistency implications
- User-facing degradation
```

---

## 6. Code Evolution & Patterns

### Pattern Recognition
```
What design patterns are used in this codebase?
- Architectural patterns (MVC, hexagonal, CQRS)
- Structural patterns (repository, factory, adapter)
- Behavioral patterns (strategy, observer, command)
- Anti-patterns to watch for
```

### Technical Debt Identification
```
Identify technical debt:
- Deprecated dependencies
- TODO/FIXME comments
- Duplicate code
- Overly complex functions
- Missing tests for critical paths
```

### Refactoring Impact Assessment
```
If I refactor [component], what are the implications?
- Direct code changes required
- Test updates needed
- API contract changes
- Migration requirements
- Rollback strategy
```

---

## 7. Integration Points

### API Contract Analysis
```
Document the API contracts:
- Endpoints and HTTP methods
- Request/response schemas
- Authentication requirements
- Rate limiting
- Versioning strategy
```

### Event/Message Schema Analysis
```
Analyze event-driven communication:
- Event types and their schemas
- Publishers and subscribers
- Delivery guarantees
- Dead letter handling
- Schema evolution strategy
```

### Third-Party Integration Mapping
```
Map all third-party integrations:
- APIs consumed
- Authentication methods
- Rate limits and quotas
- Fallback strategies
- Data synchronization patterns
```

---

## 8. Meta-Prompts for Exploration

### Unknown Unknowns Discovery
```
What aspects of this codebase might I be missing?
- Hidden configuration
- Implicit conventions
- Tribal knowledge assumptions
- Edge cases in error handling
- Undocumented behaviors
```

### Cross-Cutting Concerns
```
How are cross-cutting concerns handled?
- Logging and observability
- Error handling and reporting
- Transaction management
- Caching strategies
- Feature flags
```

### "What If" Scenarios
```
What if [scenario]?
- Traffic spikes 10x
- Database becomes unavailable
- Third-party API times out
- Credentials expire mid-operation
- Two users modify the same resource simultaneously
```

---

## Usage Tips

1. **Start broad, then narrow**: Begin with architecture questions before diving into specific components

2. **Follow the data**: Tracing data flow often reveals the most about system behavior

3. **Question defaults**: Default configurations often hide important assumptions

4. **Test your understanding**: After exploration, try to predict behavior before verifying

5. **Document discoveries**: Create diagrams and notes as you explore - future you will thank you

6. **Look for the seams**: Integration points and boundaries reveal architectural decisions

7. **Read tests first**: Test files often document expected behavior better than code comments

---

## Quick Reference Commands

```bash
# Find entry points
grep -r "if __name__" --include="*.py"
grep -r "main(" --include="*.go"

# Find configuration loading
grep -r "getenv\|environ\|config" --include="*.py"
grep -r "process.env" --include="*.ts"

# Find database operations
grep -r "SELECT\|INSERT\|UPDATE\|DELETE" --include="*.py"
grep -r "prisma\.\|db\." --include="*.ts"

# Find API endpoints
grep -r "@app\.\|@router\." --include="*.py"
grep -r "app\.(get\|post\|put\|delete)" --include="*.ts"

# Find error handling
grep -r "try:\|except\|raise" --include="*.py"
grep -r "try {\|catch\|throw" --include="*.ts"
```

---

*Last updated: 2025-01-20*
