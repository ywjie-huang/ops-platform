# Dashboard Duty Homepage Design

## Summary

This redesign shifts the dashboard from a generic summary page to a duty-focused operations homepage for on-call engineers and SREs. The first viewport should answer three questions in order: what is wrong now, what is affected, and where should I go next.

## Users

- On-call operations engineers
- SREs handling active incidents
- Platform admins doing a quick morning or shift handoff scan

## Design Direction

- Register: product
- Color strategy: restrained
- Theme: light desktop workspace in a focused daytime operations setting
- References: Linear for composure, Stripe Dashboard for hierarchy, internal monitoring tools for density

## Information Hierarchy

1. Current risk summary
2. Today focus list
3. Actionable shortcuts with state context
4. Trend and background telemetry
5. Recent activity

## Layout Strategy

- Replace the large welcome block with a compact page heading and shift meta
- Promote a top status strip with four action-oriented metrics
- Make “Today Focus” the dominant area in the main column
- Move alert trend, quick actions, and asset distribution into secondary support zones
- Keep recent activity, but reduce its visual dominance

## Required States

- Calm/default day with low incident count
- Busy incident day with several high-priority items
- Empty focus list
- Loading skeleton equivalent for future implementation

## Prototype Scope

- Single-page preview only
- Static data, no backend integration
- Light interaction polish for tabs and emphasis only
- Independent localhost preview without modifying current dashboard behavior
