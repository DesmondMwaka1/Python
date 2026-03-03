a = [1, 6, 4, 2, 7, 9, 4, 2, 4, 2, 9, 0, 7]

def merge_sort(iter_list): # Renamed function to reflect its true purpose (sorts/merges)
    # 1. Base Case (Stop the recursion)
    # The list is already sorted if it has 0 or 1 element.
    if len(iter_list) <= 1:
        return

    # 2. Divide
    mid = len(iter_list) // 2
    left_iter = iter_list[:mid]
    right_iter = iter_list[mid:]
    
    # Recursive calls to sort the halves
    merge_sort(left_iter)
    merge_sort(right_iter)
    
    # 3. Merge (The sorting step)
    i = 0  # Iterator for the left half
    j = 0  # Iterator for the right half
    k = 0  # Iterator for the main list (iter_list)
    
    # While both sublists have elements to compare
    while i < len(left_iter) and j < len(right_iter): # Corrected boolean logic
        if left_iter[i] < right_iter[j]:
            iter_list[k] = left_iter[i]
            i += 1
        else:
            iter_list[k] = right_iter[j]
            j += 1
        k += 1
        
    # Append any remaining elements from the left list
    while i < len(left_iter):
        iter_list[k] = left_iter[i]
        i += 1
        k += 1
        
    # Append any remaining elements from the right list
    while j < len(right_iter):
        iter_list[k] = right_iter[j]
        j += 1
        k += 1
            
# Call the function
merge_sort(a)
print(f"The sorted list is: {a}")