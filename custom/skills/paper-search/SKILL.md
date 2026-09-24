---
name: paper-search
description: Find and verify scholarly papers via the OpenAlex API — keyword search, DOI lookup, citation counts, open-access PDF links. Use when asked to find literature, check whether a paper exists, resolve a half-remembered citation, count citations, or build a reading list. Free, no API key. Covers geoscience, engineering and physical sciences, where PubMed-based tools do not.
---

# Paper search via OpenAlex

[OpenAlex](https://openalex.org) is a free, fully open index of ~250M scholarly works.
**No API key, no account, no rate-limit negotiation.** Prefer it as the default
literature tool.

## Why this rather than the other search skills

`citation-management` and `literature-review` lean on PubMed and Google Scholar;
`research-lookup` needs a paid Parallel or Perplexity key. For **geoscience,
geothermal, and engineering** that is the wrong coverage and an unnecessary
dependency — PubMed indexes almost none of this group's literature. Use those skills
for biomedical work or when a formal PRISMA review is the deliverable. Use this one
to find, check, or resolve a paper.

## Always send an identifying email

Add `mailto=<your-email>` to every request. It puts you in OpenAlex's polite pool,
which is faster and more reliable. Not a credential — do not treat it as a secret,
and do not invent one; use the address the user has configured in git.

## The four calls that cover almost everything

Base URL is `https://api.openalex.org`. Use `curl -sS`.

**1. Keyword search** — ranked by relevance:

```bash
curl -sS "https://api.openalex.org/works?search=enhanced+geothermal+system&per-page=25&mailto=EMAIL"
```

**2. Filtered and sorted** — the workhorse. Filters are comma-separated (AND):

```bash
curl -sS "https://api.openalex.org/works?filter=title.search:geothermal,publication_year:>2023,is_oa:true&sort=cited_by_count:desc&per-page=25&mailto=EMAIL"
```

Useful filters: `publication_year:>2020` or `2015-2020`, `is_oa:true`,
`type:article`, `cited_by_count:>100`, `authorships.institutions.ror:<ror-id>`,
`primary_topic.id:<id>`, `has_doi:true`.

**3. DOI lookup** — resolve or verify one paper. Pass the full DOI URL as the path:

```bash
curl -sS "https://api.openalex.org/works/https://doi.org/10.1016/j.geothermics.2007.03.003?mailto=EMAIL"
```

**4. Trim the payload with `select`.** Full records are large and mostly noise:

```bash
&select=id,doi,display_name,publication_year,cited_by_count,authorships,best_oa_location
```

Use `select` on every multi-result call. Reading 25 full records wastes a great deal
of context for fields you will not use.

## Reading the response

- `meta.count` — total matches. **Report it.** "93,797 papers match" is a different
  answer from "3 papers match" and changes what the user should do next.
- `display_name` — title. `publication_year`, `cited_by_count` — as named.
- `authorships[].author.display_name` — authors, in order.
- `best_oa_location.pdf_url` — a legally free PDF when one exists, else `null`.
  This is what to hand to a download step; do not guess publisher URLs.
- `abstract_inverted_index` — the abstract as a position map, not a string. It can be
  reconstructed by sorting words by position, but prefer fetching the paper over
  reassembling this.
- `primary_topic`, `concepts` — OpenAlex's own subject tags, useful for widening a
  search that came back thin.

## Rules

- **Never state a citation you have not seen in a response.** This skill exists so
  that titles, years, authors and DOIs come from the index rather than from memory.
  A plausible-looking fabricated citation is the single most damaging failure mode in
  academic work, and it is not recoverable once it reaches a manuscript.
- **If a search returns nothing, say so.** Do not substitute a paper you half
  remember. Widen the query, drop a filter, or try `concepts` — then report honestly.
- **`cited_by_count` is a popularity signal, not a quality one.** Report it as a
  number; do not launder it into a judgement about whether work is good.
- Paginate with `page=` (up to 10k results) or `cursor=*` beyond that. Do not fetch
  hundreds of records to answer a question about a handful.
- Recent preprints and very new papers may be missing or under-counted. For an
  exhaustive systematic review, use this as one source among several, not the only one.

## Composes with

`custom-deep-research` for a full citation-grounded pipeline — this skill is a good
Phase 1 discovery tool for it. `citation-management` for turning what you find into
formatted BibTeX.
