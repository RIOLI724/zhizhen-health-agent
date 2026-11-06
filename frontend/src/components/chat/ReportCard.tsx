import type { ReportData } from "@/lib/types";

interface ReportCardProps {
  report: ReportData;
}

export function ReportCard({ report }: ReportCardProps) {
  return (
    <section className="report">
      <div className="report__head">
        <span className="report__tag">样例报告</span>
        <strong>{report.title}</strong>
      </div>

      <div className="report__table-wrap">
        <table className="report__table">
          <thead>
            <tr>
              <th>指标</th>
              <th>结果</th>
              <th>参考</th>
            </tr>
          </thead>
          <tbody>
            {report.rows.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td
                  className={`report__value report__value--${row.flag}`}
                >
                  {row.value}
                  <small>{row.unit}</small>
                </td>
                <td>{row.range}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="report__note">{report.note}</p>
    </section>
  );
}
