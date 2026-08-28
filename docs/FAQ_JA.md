# FAQ（日本語）

## これは何を解決するものですか？

AIが外部記憶から「関連する情報」を見つけられても、その情報が**現在有効な判断とは限らない**という問題を扱います。

たとえば、同じ保存領域に次のものが共存することがあります。

- 過去に採用していた判断
- 現在の正式判断
- まだ未確定の案
- 将来の日付から有効になる方針
- 別案件・別subjectの似た値

Context Routerでは、広くContextを読む前にResolution Kernelで対象scopeとcurrent decisionを解決し、その後に必要なContextだけを選択して読みます。

さらに、ユーザーが「この保存済み資料を読んで」とSourceを明示した場合に、会話要約やAI内部Memoryで代用しないための **Explicit Source Read Gate** も扱います。

## 「このGitHubファイルを見て」と言ったら何が変わるのですか？

Source指定が明示された場合、その指定がretrieval requirementになります。

想定する挙動は次の通りです。

1. 指定Sourceを実際に検索・取得・閲覧する
2. その実読前に、Source由来の内容を確認済みとして答えない
3. 取得できない場合は、過去チャットやAI内部Memoryから再構成して「読んだ」ことにしない
4. Source依存の主張は `VERIFY` / `UNKNOWN` としてfail-closedする
5. ただし無関係なCOLD履歴まで広く読む必要はない

つまり、`read little`は「必要なSourceを読まなくてよい」という意味ではありません。詳しくは [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md) を参照してください。

## RAGや検索の代わりですか？

いいえ。RAGや検索を置き換えるものとしては設計していません。

検索は「何が関連しているか」を見つけるのに有効です。一方、このreferenceが主に扱うのは、関連候補の中から**どの判断をcurrentとして扱うか**、そしてユーザーが明示したSourceを別の記憶で代用しないこと、という別の問題です。

そのため、retrievalの前後に組み合わせて使う補完的なarchitectureとして考えています。

## AIの間違いやハルシネーションを防げますか？

保証しません。

この設計は、古い判断の復活、複数current候補、未確定案の誤昇格、future-effective decisionの早期採用、明示Source未読のままの回答など、外部Contextのdecision resolution / source groundingに由来する一部の失敗を明示的に扱うものです。

すべてのAI誤りを防ぐ仕組みではありません。詳しくは [`LIMITATIONS.md`](LIMITATIONS.md) を参照してください。

## CodexやChatGPTの利用量は減りますか？

減ることを保証していません。

必要なContextだけ読む設計は不要な広域読込を避ける方向に働きますが、モデル、製品、作業内容、共有利用枠などに依存するため、token costやusage limit reductionを一般化した主張にはしていません。

## 85,000/85,000 PASSはこの公開コードのテスト数ですか？

違います。

公開repoで第三者がそのまま再現できるreference testは**7/7**です。

`85,000/85,000`などの大きな数値は、より大きなprivate implementationで実施したproperty / regression validationの匿名化済みaggregate evidenceです。公開最小実装そのものが85,000ケースを実行するという意味ではありません。

同様に、Explicit Source Read Gateの`10/10 PASS`とlive dogfood smokeの`P1–P5 PASS`も、より大きなintegration layerでのsanitized evidenceです。公開Python resolver単体が外部Sourceをfetchするわけではありません。

## なぜUNKNOWNやCONFLICTを返すのですか？

情報が足りない、または複数のauthoritative candidateが残っているときに、AIがもっともらしい答えを補完してしまうことを避けるためです。

基本ルールは次の通りです。

```text
0 authoritative survivors  -> UNKNOWN
1 authoritative survivor   -> freshness evaluation
2+ authoritative survivors -> CONFLICT
```

壊れたrelationなどは `DATA_ERROR`、選択したrecordの再確認が必要なら `VERIFY` として扱います。

指定Sourceを読めなかった場合も、Source依存の主張をMemoryで補完せず `VERIFY` / `UNKNOWN` に残すのがSource Read Gateの考え方です。

## HOT / WARM / COLDとは何ですか？

Contextを読む優先度・条件を分ける考え方です。

- **HOT**: 対象のcurrent stateやactive decisionなど、直接必要なもの
- **WARM**: Production ruleやmigration procedureなど、条件が発火したときだけ読むもの
- **COLD**: 古い履歴や低確率でしか必要にならない情報

「念のため全部読む」のではなく、Resolution後のscopeに合わせて必要な範囲だけ読むことを目的にしています。

ただし、ユーザーが明示したSourceの実読は、それが今回の作業に必要ならCOLD broad readとは扱いません。

## このrepoは完成した導入キットですか？

いいえ。

このpublic repoは **Why / What / Evidence** を第三者が確認できるようにするためのsanitized referenceです。

workspace固有の完成テンプレート、migration package、private production evidence、内部運用情報などは含めていません。

## Source Read Gateは公開Pythonコードに実装されていますか？

いいえ。

`reference/minimal_resolver.py` はdecision resolutionの最小referenceです。外部Sourceへの接続・fetch・閲覧確認までは実装していません。

公開repoでは、Source Read Gateの**contract・architecture・validation evidence・limitations**を公開しています。これにより、公開最小コードの範囲を過大に見せないようにしています。

## 自由にコピー・再利用できますか？

現時点ではopen-source licenseを設定していません。

Publicで閲覧できることと、自由な再利用を許諾することは別です。ライセンス方針は別途明示的に決定します。
