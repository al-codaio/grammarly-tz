I'm having multiple issues with Grammarly: it's not working in Google Docs, my Premium features aren't showing up even though I paid, and when I try to reinstall the Chrome extension it says 'installation failed'. What should I do?



# DICL Variant Demonstration

## Test Query
"How do I use Grammarly's new AI citation checker with APA 7th edition in Google Docs? It keeps formatting in-text citations incorrectly."

## Results Summary

### DICL Variant (gpt_4o_mini_dicl)
- **Confidence**: 0.98
- **Key Strengths**:
  - Provides specific, step-by-step instructions
  - Acknowledges the frustration and offers empathetic support
  - Includes troubleshooting tips (browser update, cache clearing)
  - Mentions specific APA 7th edition formatting rules (Author, Year)
  - Provides examples of multiple author citations (et al.)
  - Suggests consulting Grammarly Handbook and support resources
  - More comprehensive and contextual response

### Standard gpt_4o_mini
- **Confidence**: 0.95
- **Response**: More generic, starts with installation steps
- Missing specific troubleshooting and formatting examples

### Standard gpt_4o
- **Confidence**: 0.95
- **Response**: Basic troubleshooting steps
- Less detailed than DICL variant

## Why DICL is Better

1. **Contextual Learning**: DICL uses 982 examples from actual Grammarly support articles
2. **Specific Examples**: The system has 11 citation-related examples that help provide more accurate responses
3. **Better Problem Understanding**: DICL variant immediately acknowledges the specific issue with formatting
4. **Comprehensive Solutions**: Provides both immediate fixes and long-term solutions

## Testing in TensorZero UI

You can test these variants yourself at http://localhost:4000:

1. Navigate to Inferences
2. Search for these inference IDs:
   - DICL: `0198b07d-7036-7933-93bb-03c3c851138c`
   - gpt_4o_mini: `0198b07d-ea6d-73c0-8242-e614a63c1abe`
   - gpt_4o: `0198b07e-35bd-7b81-8013-1152a5db1a75`
3. Use the "Try with variant" dropdown to compare responses

## Configuration

Current weights in `tensorzero.toml`:
- `gpt_4o_mini_dicl`: weight = 1 (always selected by default)
- `gpt_4o_mini`: weight = 0
- `gpt_4o`: weight = 0

This ensures DICL is used in production while still allowing comparison testing.