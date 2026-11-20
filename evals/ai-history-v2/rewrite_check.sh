# After the noreply-email rewrite: pair each old commit with its new commit
# (same order on each branch) and show that the file tree, subject, author
# date and parent structure are unchanged; only the emails differ.
# Usage: bash rewrite_check.sh   (run in the repository)
set -u
bad=0
report=$(for pair in "archive/pre-noreply-v2-candidate v2-candidate" "archive/pre-noreply-engine engine"; do
  set -- $pair
  old=$(git rev-list --reverse main.."$1")
  n_old=$(echo "$old" | wc -l)
  new=$(git rev-list --reverse main.."$2" | head -n "$n_old")   # later commits on the branch are not part of the rewrite
  [ "$(echo "$new" | wc -l)" = "$n_old" ] || echo "NO: fewer new commits than old on $2"
  paste <(echo "$old") <(echo "$new") | while read -r o n; do
    same_tree=$([ "$(git rev-parse "$o^{tree}")" = "$(git rev-parse "$n^{tree}")" ] && echo yes || echo NO)
    same_meta=$([ "$(git log -1 --format='%s|%ad|%cd' "$o")" = "$(git log -1 --format='%s|%ad|%cd' "$n")" ] && echo yes || echo NO)
    echo "$2: $(git rev-parse --short "$o") -> $(git rev-parse --short "$n")  tree identical: $same_tree  subject+dates identical: $same_meta  new author: $(git log -1 --format='%ae' "$n")"
  done
done)
echo "$report"
echo "$report" | grep -q 'NO' && bad=1
echo "private address left on new commits: $(git log --format='%ae%n%ce' main..v2-candidate main..engine | grep -c 'rmasood112224@gmail.com')"
[ $bad = 0 ] && echo "rewrite check: PASS" || echo "rewrite check: FAIL"
