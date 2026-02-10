# TypeScript Static Analyzer

A TypeScript-focused static analysis toolchain that covers three stages of compilation: AST parsing, intermediate representation generation, and control flow graph construction.

Built as part of a multi-language static analysis framework during the Compiler Design course at Fudan University.

## Pipeline

```
TypeScript Source Code
        │
        ▼
┌─────────────────┐
│  Tree-sitter    │  Stage 1: Lexical & Syntax Analysis
│  AST Parsing    │  Parse source into Abstract Syntax Tree
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Glang IR       │  Stage 2: IR Generation
│  Generation     │  Transform AST into language-independent IR
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Control Flow   │  Stage 3: CFG Construction
│  Graph Analysis │  Build control flow graph from IR
└─────────────────┘
```

## Project Structure

```
typescript-static-analyzer/
├── parser/
│   └── typescript_parser.py       # AST → IR transformation (~900 lines)
├── analysis/
│   └── control_flow.py            # IR → CFG construction (~350 lines)
├── grammar/
│   └── typescript_grammar.js      # Tree-sitter grammar for TypeScript
├── tests/
│   ├── expressions/               # Stage 1 & 2: parsing test cases
│   │   ├── assignment_expression.ts
│   │   ├── augmented_assignment_expression.ts
│   │   ├── binary_expression.ts
│   │   ├── call_expression.ts
│   │   ├── member_expression.ts
│   │   ├── unary_expression.ts
│   │   └── variable_declaration.ts
│   └── control_flow/              # Stage 3: CFG test cases
│       ├── break.ts
│       ├── continue.ts
│       ├── try.ts
│       └── yield.ts
├── .gitignore
└── README.md
```

## Stage 1 — AST Parsing

Uses [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) with a custom TypeScript grammar (`grammar/typescript_grammar.js`) to parse source code into an Abstract Syntax Tree. Tree-sitter provides incremental parsing and robust error recovery, making it suitable for static analysis on real-world code.

## Stage 2 — IR Generation

The core of this project. The parser (`parser/typescript_parser.py`) traverses the Tree-sitter AST and transforms it into a language-independent intermediate representation (Glang IR). This allows downstream analyses (like CFG) to work uniformly across different source languages.

### Supported Constructs

**Expressions**
- Assignment & augmented assignment (`=`, `+=`, `-=`, etc.)
- Binary & unary expressions
- Member access & subscript (array indexing)
- Function calls with type arguments
- Ternary, new, arrow functions, function expressions
- Template strings with substitutions
- Await, yield, as/satisfies, type assertions
- Array/object literals, spread, destructuring patterns

**Declarations**
- Variable & lexical declarations (with type annotations)
- Function, method, generator declarations
- Class & abstract class (inheritance, decorators, static blocks)
- Interface, enum, type alias, module declarations

**Statements**
- Control flow: `if`, `for`, `for...in`, `while`, `do...while`, `switch`
- Jump: `break`, `continue`, `return`, `throw`
- Exception: `try...catch...finally`
- Module: `import`, `export` (named, default, namespace, re-export)
- Labeled, with, expression statements

### IR Example

Input:
```typescript
let x: number = a + b;
```

IR output:
```python
[
  {"assign_stmt": {"target": "%v0", "operator": "+", "operand": "a", "operand2": "b"}},
  {"variable_decl": {"attr": [], "data_type": "number", "name": "x"}},
  {"assign_stmt": {"target": "x", "operand": "%v0"}}
]
```

## Stage 3 — Control Flow Graph

The CFG analyzer (`analysis/control_flow.py`) takes the IR and constructs a control flow graph using NetworkX, modeling all branching and looping behavior.

### Supported Patterns

| Pattern | CFG Edges |
|---------|-----------|
| `if / else` | IF_TRUE, IF_FALSE branches |
| `while` | LOOP_TRUE (body), LOOP_FALSE (exit) |
| `do...while` | LOOP_TRUE entry, conditional back-edge |
| `for` | FOR_CONDITION → LOOP_TRUE / LOOP_FALSE with init & update |
| `for...in` | Same as while (iterator-based) |
| `try / catch / finally` | TRY → catch/finally chains |
| `break` | BREAK — terminates loop/switch |
| `continue` | CONTINUE — jumps to next iteration |
| `return` | RETURN — exits method |
| `yield` | YIELD — generator suspension point |

## Tech Stack

- **Language:** Python
- **Parser Generator:** Tree-sitter
- **Intermediate Representation:** Glang IR
- **Graph Library:** NetworkX

## Note

This repository contains the TypeScript-specific components I implemented for a multi-language static analysis framework. The full framework (base classes, config, utilities) is required to run the parser and analyzer end-to-end. These files demonstrate the design and implementation of language-specific IR generation and control flow analysis.

## License

Developed as coursework at Fudan University.
