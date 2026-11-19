import type { Overview } from '../../api/client'
import { IssuesCard, RosterSummary, TargetTable } from './BottomCards'

export function BottomCardsRow({ ov }: { ov: Overview }) {
  return (
    <section className="row bottom">
      <IssuesCard ov={ov} />
      <TargetTable ov={ov} />
      <RosterSummary ov={ov} />
    </section>
  )
}
