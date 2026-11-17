# shoppingmall

무신사를 참고한 패션 쇼핑몰 데이터 모델링 실습 저장소입니다.

## 진행 현황
| 회차 | 문서 | 상태 |
|---|---|---|
| 용어 | `modeling/00_용어대응표.md` | 수업 PPT(핵심 데이터 모델링) 용어 정리 |
| 초안 | `modeling/00_초기설계안_보존.md` | 처음 만든 설계안 보존 |
| 1. 고객 | `modeling/01_고객.md` | 확정 (테이블 10개) |
| 2. 카테고리 | `modeling/02_카테고리.md` | 확정 (테이블 4개) |
| 3. 상품 | `modeling/03_상품.md` | 확정 (테이블 14개) |
| 4. 장바구니·주문 | `modeling/04_주문.md` | 확정 (테이블 6개) |
| 5. 결제·배송 | `modeling/05_결제_배송.md` | 확정 (테이블 9개) |
| ERD | `modeling/erd/` | Mermaid(`.mmd`, 회차별 + 전체), draw.io(`erd_전체.drawio`, 회차별 페이지) |

## ERD 다시 만들기
설계 문서(`modeling/0*_*.md`)의 테이블 정의 표를 읽어 `modeling/erd/`를 다시 생성합니다.

```
python3 scripts/gen_erd.py modeling
```
